import time, sys

num = 100
if len(sys.argv) > 1:
    num = int(sys.argv[1])
print num

for x in range(num):
    print 'blah'
    time.sleep(1)
