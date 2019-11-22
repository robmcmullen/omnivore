#! python3

"""This is an APNG module, which can create apng file from pngs

Reference:
http://littlesvr.ca/apng/
http://wiki.mozilla.org/APNG_Specification
https://www.w3.org/TR/PNG/
"""

import struct
import binascii
import itertools
import io

__version__ = "0.2.1"

try:
	import PIL.Image
except ImportError:
	# Without Pillow, apng can only handle PNG images
	pass

try:
	import numpy as np

	isnumpy = lambda data: hasattr(data, "flat")
except ImportError:
	isnumpy = lambda data: False

PNG_SIGN = b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"

# http://www.libpng.org/pub/png/spec/1.2/PNG-Chunks.html#C.Summary-of-standard-chunks
CHUNK_BEFORE_IDAT = {
	"cHRM", "gAMA", "iCCP", "sBIT", "sRGB", "bKGD", "hIST", "tRNS", "pHYs",
	"sPLT", "tIME", "PLTE"
}

def is_png(png):
	"""Test if ``png`` is a valid PNG file by checking the signature.
	
	:arg png: If ``png`` is a :any:`path-like object` or :any:`file-like object`
		object, read the content into bytes.
	:type png: path-like, file-like, or bytes
	:rtype: bool
	"""
	if isinstance(png, str) or hasattr(png, "__fspath__"):
		with open(png, "rb") as f:
			png_header = f.read(8)		
	elif hasattr(png, "read"):
		position = png.tell()
		png_header = png.read(8)
		png.seek(position)
	elif isinstance(png, bytes):
		png_header = png[:8]
	elif isnumpy(png):
		png_header = bytes(png.flat[:8])
	else:
		raise TypeError("Must be file, bytes, or str but get {}"
				.format(type(png)))
			
	return png_header == PNG_SIGN
			
def chunks_read(b):
	"""Parse PNG bytes into different chunks, yielding (type, data). 
	
	@type is a string of chunk type.
	@data is the bytes of the chunk. Including length, type, data, and crc.
	"""
	# skip signature
	i = 8
	# yield chunks
	while i < len(b):
		data_len, = struct.unpack("!I", b[i:i+4])
		type = b[i+4:i+8].decode("latin-1")
		yield type, b[i:i+data_len+12]
		i += data_len + 12

def chunks(png):
	"""Yield ``(chunk_type, chunk_raw_data)`` from ``png``.
	
	.. note::
	
		``chunk_raw_data`` includes chunk length, type, and CRC.
	
	:arg png: If ``png`` is a :any:`path-like object` or :any:`file-like object`
		object, read the content into bytes.
	:type png: path-like, file-like, or bytes
	:rtype: Generator[tuple(str, bytes)]
	"""
	if not is_png(png):
		# convert to png
		if isinstance(png, bytes):
			with io.BytesIO(png) as f:
				with io.BytesIO() as f2:
					PIL.Image.open(f).save(f2, "PNG", optimize=True)
					png = f2.getvalue()
		elif isnumpy(png):
			with io.BytesIO() as f2:
				im = PIL.Image.fromarray(png).save(f2, "PNG", optimize=True)
				png = np.fromstring(f2.getvalue(), dtype=np.uint8)
		else:
			with io.BytesIO() as f2:
				PIL.Image.open(png).save(f2, "PNG", optimize=True)
				png = f2.getvalue()
	
	if isinstance(png, str) or hasattr(png, "__fspath__"):
		# path like
		with open(png, "rb") as f:
			png = f.read()		
	elif hasattr(png, "read"):
		# file like
		png = png.read()
	elif isnumpy(png):
		# numpy array
		png = png.tostring()
		
	return chunks_read(png)
		
def make_chunk(type, data):
	"""Create a raw chunk by composing chunk's ``type`` and ``data``. It
	calculates chunk length and CRC for you.

	:arg str type: PNG chunk type.
	:arg bytes data: PNG chunk data, **excluding chunk length, type, and CRC**.
	:rtype: bytes
	"""
	out = struct.pack("!I", len(data))
	data = type.encode("latin-1") + data
	out += data + struct.pack("!I", binascii.crc32(data) & 0xffffffff)
	return out
	
class PNG:
	"""Represent PNG image. This class should only be initiated with
	classmethods."""
	def __init__(self):
		self.hdr = None
		self.end = None
		self.width = None
		self.height = None
		self.chunks = []
		
	def init(self):
		"""Extract some info from chunks"""
		for type, data in self.chunks:
			if type == "IHDR":
				self.hdr = data
			elif type == "IEND":
				self.end = data
				
		if self.hdr:
			# grab w, h info
			self.width, self.height = struct.unpack("!II", self.hdr[8:16])
			
	@classmethod
	def open(cls, png):
		"""Open a PNG file.
		
		:arg png: See :func:`chunks`.
		:rtype: :class:`PNG`
		"""
		o = cls()
		o.chunks = list(chunks(png))
		o.init()
		return o
		
	@classmethod
	def from_chunks(cls, chunks):
		"""Construct PNG from raw chunks.
		
		:arg chunks: A list of ``(chunk_type, chunk_raw_data)``. Also see
			:func:`chunks`.
		:type chunks: list[tuple(str, bytes)]
		"""
		o = cls()
		o.chunks = chunks
		o.init()
		return o
		
	def to_bytes(self):
		"""Convert entire image to bytes.
		
		:rtype: bytes
		"""
		chunks = [PNG_SIGN]
		chunks.extend(c[1] for c in self.chunks)
		return b"".join(chunks)
		
	def save(self, file):
		"""Save entire image to a file.

		:arg file: The destination.
		:type file: path-like or file-like
		"""
		if isinstance(file, str) or hasattr(file, "__fspath__"):
			with open(file, "wb") as f:
				f.write(self.to_bytes())
		else:
			file.write(self.to_bytes())
		
class FrameControl:
	"""A data class holding fcTL info."""
	def __init__(self, width=None, height=None, x_offset=0, y_offset=0, delay=100, delay_den=1000, depose_op=1, blend_op=0):
		"""Parameters are assigned as object members. See `https://wiki.mozilla.org/APNG_Specification <https://wiki.mozilla.org/APNG_Specification#.60fcTL.60:_The_Frame_Control_Chunk>`_ for the detail of fcTL.
		"""
		self.width = width
		self.height = height
		self.x_offset = x_offset
		self.y_offset = y_offset
		self.delay = delay
		self.delay_den = delay_den
		self.depose_op = depose_op
		self.blend_op = blend_op
		
	def to_bytes(self):
		"""Convert to bytes.
		
		:rtype: bytes
		"""
		return struct.pack("!IIIIHHbb", self.width, self.height, self.x_offset, self.y_offset, self.delay, self.delay_den, self.depose_op, self.blend_op)
		
	@classmethod
	def from_bytes(cls, b):
		"""Contruct fcTL info from bytes.
		
		:arg bytes b: The length of ``b`` must be *28*, excluding sequence
			number and CRC.
		"""
		return cls(*struct.unpack("!IIIIHHbb", b))

class APNG:
	"""Represent APNG image."""
	def __init__(self, num_plays=0):
		"""APNG is composed by multiple PNGs, which can be inserted with 
		:meth:`append`.
		
		:arg int num_plays: Number of times to loop. 0 = infinite.
			
		:var frames: Frames of APNG, a list of ``(png, control)`` tuple.
		:vartype frames: list[tuple(PNG, FrameControl)]
		:var int num_plays: same as ``num_plays``.
		"""
		self.frames = []
		self.num_plays = num_plays

	def __str__(self):
		return f"APNG: {len(self.frames)} frames, # plays={self.num_plays}"
		
	def append(self, png, **options):
		"""Read a PNG file and append one frame.
		
		:arg png: See :meth:`PNG.open`.
		:arg options: See :class:`FrameControl`.
		"""
		png = PNG.open(png)
		control = FrameControl(**options)
		if control.width is None:
			control.width = png.width
		if control.height is None:
			control.height = png.height
		self.frames.append((png, control))
		
	def to_bytes(self):
		"""Convert entire image to bytes.
		
		:rtype: bytes
		"""
		
		# grab the chunks we needs
		out = [PNG_SIGN]
		# FIXME: it's tricky to define "other_chunks". HoneyView stop the 
		# animation if it sees chunks other than fctl or idat, so we put other
		# chunks to the end of the file
		other_chunks = []
		seq = 0
		
		# for first frame
		png, control = self.frames[0]
		
		# header
		out.append(png.hdr)
		
		# acTL
		out.append(make_chunk("acTL", struct.pack("!II", len(self.frames), self.num_plays)))
		
		# fcTL
		if control:
			out.append(make_chunk("fcTL", struct.pack("!I", seq) + control.to_bytes()))
			seq += 1
		
		# and others...
		idat_chunks = []
		for type, data in png.chunks:
			if type in ("IHDR", "IEND"):
				continue
			if type == "IDAT":
				# put at last
				idat_chunks.append(data)
				continue
			out.append(data)
		out.extend(idat_chunks)
		
		# FIXME: we should do some optimization to frames...
		# for other frames
		for png, control in self.frames[1:]:
			# fcTL
			out.append(
				make_chunk("fcTL", struct.pack("!I", seq) + control.to_bytes())
			)
			seq += 1
			
			# and others...
			for type, data in png.chunks:
				if type in ("IHDR", "IEND") or type in CHUNK_BEFORE_IDAT:
					continue
				elif type == "IDAT":
					# convert IDAT to fdAT
					out.append(
						make_chunk("fdAT", struct.pack("!I", seq) + data[8:-4])
					)
					seq += 1
				else:
					other_chunks.append(data)
		
		# end
		out.extend(other_chunks)
		out.append(png.end)
		
		return b"".join(out)
		
	@classmethod
	def from_files(cls, files, **options):
		"""Create APNG from multiple files.
		
		This is same as::
		
			im = APNG()
			for file in files:
				im.append(file, **options)
				
		:arg list files: A list of file. See :meth:`PNG.open`.
		:arg options: Options for :class:`FrameControl`.
		:rtype: APNG
		"""
		o = cls()
		for file in files:
			o.append(file, **options)
		return o
		
	@classmethod
	def open(cls, file):
		"""Open an APNG file.
		
		:arg file: See :func:`chunks`.
		:rtype: APNG
		"""
		hdr = None
		head_chunks = []
		end = ("IEND", make_chunk("IEND", b""))
		
		frame_chunks = []
		frames = []
		num_plays = 0
		
		control = None
		
		for type, data in chunks(file):
			if type == "IHDR":
				hdr = data
				frame_chunks.append((type, data))
			elif type == "acTL":
				num_frames, num_plays = struct.unpack("!II", data[8:-4])
				continue
			elif type == "fcTL":
				if any(type == "IDAT" for type, data in frame_chunks):
					# IDAT inside chunk, go to next frame
					frame_chunks.append(end)
					frames.append((PNG.from_chunks(frame_chunks), control))
					
					control = FrameControl.from_bytes(data[12:-4])
					hdr = make_chunk("IHDR", struct.pack("!II", control.width, control.height) + hdr[16:-4])
					frame_chunks = [("IHDR", hdr)]
				else:
					control = FrameControl.from_bytes(data[12:-4])
			elif type == "IDAT":
				frame_chunks.extend(head_chunks)
				frame_chunks.append((type, data))
			elif type == "fdAT":
				# convert to IDAT
				frame_chunks.extend(head_chunks)
				frame_chunks.append(("IDAT", make_chunk("IDAT", data[12:-4])))
			elif type == "IEND":
				# end
				frame_chunks.append(end)
				frames.append((PNG.from_chunks(frame_chunks), control))
				break
			elif type in CHUNK_BEFORE_IDAT:
				head_chunks.append((type, data))
			else:
				frame_chunks.append((type, data))
				
		o = cls()
		o.frames = frames
		o.num_plays = num_plays
		return o
		
	def save(self, file):
		"""Save entire image to a file.

		:arg file: The destination.
		:type file: path-like or file-like
		"""
		if isinstance(file, str) or hasattr(file, "__fspath__"):
			with open(file, "wb") as f:
				f.write(self.to_bytes())
		else:
			file.write(self.to_bytes())
