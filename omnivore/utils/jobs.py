import os, time, logging, threading, multiprocessing, queue

# Utilities for thread and process based jobs


# Don't use the logger module in anything using multiprocessing! It can cause
# deadlocks.  I.e. don't use this:
#### log = logging.getLogger("dinoteeth.job")

log = multiprocessing.log_to_stderr()


class Job(object):
    def __init__(self, job_id=None):
        self.job_id = job_id
        self.parent = None
        self.children_running = 0
        self.children_scheduled = []
        self.error = None
        self.exception = None

    def debug(self, s):
        log.debug(s)

    def __str__(self):
        status = self.get_name()
        if not self.success():
            if self.error is not None:
                status += " Failed: %s" % self.error
            else:
                status += " Exception: %s" % self.exception
        return status

    def success(self):
        return self.error is None and self.exception is None

    def get_name(self):
        return self.__class__.__name__

    def _start(self, dispatcher):
        raise RuntimeError("Abstract method")

    def _success_message(self):
        return None

    def _failed_message(self):
        return None

    def _get_status_message(self):
        if self.success():
            return self._success_message()
        else:
            return self._failed_message()

    def success_callback(self):
        """Called in main thread if job completes successfully.
        
        Note that since it occurs in the main thread, GUI methods may
        be safely called.
        """
        pass

    def failure_callback(self):
        """Called in main thread if job fails during the thread processing.
        
        Note that since it occurs in the main thread, GUI methods may be safely
        called.
        """
        pass


class ProcessJob(Job):
    def _start(self, results):
        raise RuntimeError("Abstract method")


class LargeMemoryJob(Job):
    def _start(self, results):
        raise RuntimeError("Abstract method")


class Worker(multiprocessing.Process):
    def __init__(self, job_queue, progress_queue):
        multiprocessing.Process.__init__(self)
        self._jobs = job_queue
        self._progress = progress_queue
        self.start()

    def _progress_update(self, item):
        update = ProgressReport(item)
        self._progress.put(update)

    def run(self):
        while True:
            log.debug("%s: worker waiting for job" % self.name)
            job = self._jobs.get() # block to wait for new job
            log.debug("%s: worker found job %s" % (self.name, str(job)))
            if job is None:
                # "poison pill" means shutdown this worker
                log.debug("%s: poison pill received. Stopping" % self.name)
                self._progress.put(Shutdown())
                break
            try:
                job._start(self)
            except Exception as e:
                import traceback
                job.exception = traceback.format_exc()
            self._progress.put(Finished(job))


class JobDispatcher(object):
    def __init__(self, share_input_queue_with=None):
        self._want_abort = False
        if share_input_queue_with is not None:
            self._queue = share_input_queue_with._queue
        else:
            self._queue = queue.Queue()

    def set_manager(self, manager):
        self._manager = manager

    def start_processing(self):
        raise RuntimeError("Abstract method")

    @classmethod
    def can_handle(self, job):
        return False

    def add_job(self, job):
        self._queue.put(job)

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = True
        self._queue.put(None)


class ThreadJobDispatcher(threading.Thread, JobDispatcher):
    def __init__(self, share_input_queue_with=None):
        threading.Thread.__init__(self)
        JobDispatcher.__init__(self, share_input_queue_with)
        self.log = log

    def start_processing(self):
#        self.setDaemon(True)
        self.start()

    @classmethod
    def can_handle(self, job):
        return isinstance(job, ThreadJob)

    def run(self):
        log.debug("starting thread...")
        while True:
            log.debug("%s waiting for jobs..." % self.name)
            job = self._queue.get(True) # blocking
            if job is None or self._want_abort:
                break
            try:
                job._start(self)
            except Exception as e:
                import traceback
                job.exception = traceback.format_exc()
            self._manager._job_done(job)


class ProcessJobDispatcher(ThreadJobDispatcher):
    def __init__(self, *args, **kwargs):
        ThreadJobDispatcher.__init__(self, *args, **kwargs)
        self._multiprocessing_jobs = multiprocessing.Queue()
        self._multiprocessing_progress = multiprocessing.Queue()
        self._worker = Worker(self._multiprocessing_jobs, self._multiprocessing_progress)
        log.debug("worker %s: status = %s" % (self._worker, self._worker.exitcode))

    @classmethod
    def can_handle(self, job):
        return isinstance(job, ProcessJob)

    def run(self):
        log.debug("%s: starting process job dispatcher thread..." % self.name)
        while True:
            log.debug("%s: waiting for jobs..." % self.name)
            job = self._queue.get(True) # blocking

            # Send job to worker and wait for it to finish
            log.debug("%s: sending job '%s' to process %s" % (self.name, job, self._worker))
            self._multiprocessing_jobs.put(job)
            while True:
                progress = self._multiprocessing_progress.get(True)
                if isinstance(progress, Finished):
                    self._manager._job_done(progress.job)
                    break
                elif isinstance(progress, Shutdown):
                    job = None
                    break
                else:
                    self._manager._progress_report(progress.report)

            if job is None:
                log.debug("%s: Stopping process %s" % (self.name, self._worker))
                self._worker.join()
                log.debug("%s: Exiting dispatcher %s" % (self.name, self.name))
                break


class ProgressReport(object):
    def __init__(self, job_id=None, report=None):
        self.job_id = job_id
        self.report = report

    def is_finished(self):
        return False


class Shutdown(ProgressReport):
    pass


class Finished(ProgressReport):
    def is_finished(self):
        return True


class Running(ProgressReport):
    pass


class Terminated(ProgressReport):
    pass


class LargeMemoryWorker(multiprocessing.Process):
    def __init__(self, job, progress_queue):
        multiprocessing.Process.__init__(self)
        self._job = job
        self._progress = progress_queue

    def _progress_update(self, item):
        self._progress.put(item)

    def run(self):
        self._progress.put(Running())
        try:
            self._job._start(self)
        except Exception as e:
            import traceback
            self._job.exception = traceback.format_exc()
        self._progress.put(None)


class LargeMemoryJobDispatcher(ThreadJobDispatcher):
    def __init__(self, *args, **kwargs):
        ThreadJobDispatcher.__init__(self, *args, **kwargs)
        self._multiprocessing_progress = multiprocessing.Queue()
        self._worker = None
        self._is_running = False
        self._timeout = 5

    @classmethod
    def can_handle(self, job):
        return isinstance(job, LargeMemoryJob)

    def add_job(self, job):
        self._worker = LargeMemoryWorker(job, self._multiprocessing_progress)
        log.debug("LARGEMEM: worker %s: status = %s" % (self._worker, self._worker.exitcode))
        self.start()

    def run(self):
        log.debug("LARGEMEM: %s: starting %s..." % (self.name, self._worker))
        self._worker.start()
        while True:
            log.debug("LARGEMEM: %s: waiting for progress queue" % (self.name))
            try:
                progress = self._multiprocessing_progress.get(True, timeout=1)
                log.debug("LARGEMEM: %s: got progress update from queue" % (self.name))
                if progress is None:
                    break
                elif isinstance(progress, Running):
                    self._is_running = True
                else:
                    self._manager._progress_report(progress)
            except queue.Empty:
                log.debug("LARGEMEM: %s: progress queue empty; worker %s status=%s alive=%s" % (self.name, self._worker, self._worker.exitcode, self._worker.is_alive()))
            if not self._is_running:
                log.debug("LARGEMEM: %s: waiting for confirmation that worker is running. %d seconds remaining" % (self.name, self._timeout))
                self._timeout -= 1
                if self._timeout <= 0:
                    log.debug("LARGEMEM: %s: didn't get confirmation that worker is running. Force quit!" % (self.name))
                    self._manager._progress_report(Terminated())
                    self._worker.terminate()
                    break
        log.debug("LARGEMEM: %s: Stopping process %s" % (self.name, self._worker))
        self._worker.join()
        log.debug("LARGEMEM: %s: Exiting dispatcher %s" % (self.name, self.name))
        self._manager._job_done(None, self)


class Timer(threading.Thread):
    def __init__(self, event_callback, resolution=.2):
        threading.Thread.__init__(self)
        self._event_callback = event_callback
        self._event = threading.Event()
        self._resolution = resolution
        self._expire_time = time.time()
        self._want_abort = False
        self.start()

    def run(self):
        while self._event.wait():
            while self._event.is_set():
                if self._want_abort:
                    return
                time.sleep(self._resolution)
#                log.debug("timer!!!!")
                self._event_callback()
                if time.time() > self._expire_time:
                    self.stop_ticks()
            if self._want_abort:
                return
            self._event_callback()

    def start_ticks(self, resolution, expire_time):
        self._resolution = resolution
        self._expire_time = expire_time
        self._event.set()

    def stop_ticks(self):
        if not self._want_abort:
            self._event.clear()
        log.debug("Timer.stop_ticks: timer expired!!!")

    def abort(self):
        log.debug("Timer.abort: stopping timer!!!")
        self._want_abort = True
        self._event.set()


class JobManager(object):
    def __init__(self, event_callback):
        log = logging.getLogger(self.__class__.__name__)
        self.event_callback = event_callback
        self.job_id_handlers = {}
        self._finished = queue.Queue()
        self.dispatchers = []
        self.dispatcher_classes = [LargeMemoryJobDispatcher]
        self.timer = Timer(event_callback)

    def start_ticks(self, resolution, expire_time):
        self.timer.start_ticks(resolution, expire_time)

    def stop_ticks(self):
        self.timer.stop_ticks()

    def find_dispatcher(self, job):
        for dispatcher in self.dispatchers:
            if dispatcher.can_handle(job):
                return dispatcher
        for dispatcher_cls in self.dispatcher_classes:
            if dispatcher_cls.can_handle(job):
                dispatcher = dispatcher_cls()
                dispatcher.set_manager(self)
                return dispatcher
        return None

    def start_dispatcher(self, dispatcher):
        log.debug("Adding dispatcher %s" % str(dispatcher))
        dispatcher.set_manager(self)
        dispatcher.start_processing()
        self.dispatchers.append(dispatcher)

    def add_job(self, job):
        dispatcher = self.find_dispatcher(job)
        if dispatcher is not None:
            log.debug("Adding job %s to %s" % (str(job), str(dispatcher)))
            dispatcher.add_job(job)
        else:
            log.debug("No dispatcher for job %s" % str(job))
        return dispatcher is not None

    def _progress_report(self, progress_report):
        """Called from threads to report milestones as the job works
        
        If event handler is defined, also calls that function to report to the
        UI that a job is available.
        """
        log.debug("progress report in thread: %s" % repr(progress_report))
        if self.event_callback is not None:
            self.event_callback(progress_report)

    def _job_done(self, job, dispatcher=None):
        """Called from threads to report completed jobs
        
        If event handler is defined, also calls that function to report to the
        UI that a job is available.
        """
        if job is not None:
            self._finished.put(job)
        if dispatcher is not None:
            self._finished.put(dispatcher)
        if self.event_callback is not None:
            if job is not None:
                message = job._get_status_message()
            else:
                message = None
            self.event_callback(message)

    def get_finished(self):
        done = set()
        try:
            while True:
                item = self._finished.get(False)
                if hasattr(item, "can_handle"):
                    # really a dispatcher
                    log.debug("dispatcher %s completed" % str(item))
                    item.join()
                    log.debug("dispatcher %s joined" % str(item))
                else:
                    done.add(item)
        except queue.Empty:
            pass
        for job in done:
            log.debug("job %s completed" % str(job))
            if job is None:
                # Skip any poison pill jobs
                continue
            if job.parent is not None:
                log.debug("  subjob of %s" % str(job.parent))
            if job.success():
                job.success_callback()
            else:
                job.failure_callback()
        return done

    def shutdown(self):
        for dispatcher in self.dispatchers:
            dispatcher.abort()
        self.timer.abort()
        for dispatcher in self.dispatchers:
            dispatcher.join()
        self.timer.join()

    def register_job_id_callback(self, job_id, callback):
        self.job_id_handlers[job_id] = callback

    def handle_job_id_callback(self, event):
        if hasattr(event, 'job_id'):
            job_id = event.job_id
            callback = self.job_id_handlers.get(job_id, None)
            if callback is not None:
                log.debug("handle_job_id_callback: found callback for %s!" % job_id)
                callback(event)
                if isinstance(event, Finished):
                    # automatically remove handler
                    del self.job_id_handlers[job_id]
            else:
                log.debug("handle_job_id_callback: no callback for %s!" % job_id)
        else:
            log.debug("handle_job_id_callback: no callback for generic event %s!" % event)


GlobalJobManager = None


def create_global_job_manager(callback):
    global GlobalJobManager
    if GlobalJobManager is None:
        GlobalJobManager = JobManager(callback)
    return GlobalJobManager


def get_global_job_manager():
    global GlobalJobManager
    return GlobalJobManager


if __name__ == '__main__':
    import functools

    class TestProcessSleepJob(ProcessJob):
        def __init__(self, num, sleep):
            Job.__init__(self)
            self.num = num
            self.sleep = sleep

        def get_name(self):
            return "process sleep job #%d, delay=%ss" % (self.num, self.sleep)

        def _start(self, dispatcher):
            log.debug("%s starting!" % self.get_name())
            time.sleep(self.sleep)
            dispatcher._progress_update("Update #1 for %d" % self.num)
            time.sleep(self.sleep)
            dispatcher._progress_update("Update #2 for %d" % self.num)
            time.sleep(self.sleep)
            dispatcher._progress_update("Update #3 for %d" % self.num)

    def post_event(event_name, *args):
        print(("event: %s.  args=%s" % (event_name, str(args))))

    def get_event_callback(event):
        callback = functools.partial(post_event, event)
        return callback

    def test_sleep():
        callback = get_event_callback("on_status_change")
        manager = JobManager(callback)
        dispatcher3 = ProcessJobDispatcher()
        manager.start_dispatcher(dispatcher3)
        for i in range(3):
            dispatcher_i = ProcessJobDispatcher(dispatcher3)
            manager.start_dispatcher(dispatcher_i)

        manager.add_job(TestProcessSleepJob(10, .1))
        manager.add_job(TestProcessSleepJob(11, .1))
        manager.add_job(TestProcessSleepJob(12, .3))
        manager.add_job(TestProcessSleepJob(13, .1))
        manager.add_job(TestProcessSleepJob(14, .1))
        for i in range(5):
            time.sleep(1)
            jobs = manager.get_finished()
            for job in jobs:
                print(('FINISHED:', str(job)))

    #    manager.add_job(TestProcessSleepJob(6, 1))
        manager.shutdown()
        jobs = manager.get_finished()
        for job in jobs:
            print(('FINISHED:', str(job)))
        for i in range(5):
            time.sleep(1)
            jobs = manager.get_finished()
            for job in jobs:
                print(('FINISHED:', str(job)))

    test_sleep()
