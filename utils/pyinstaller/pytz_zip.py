def pytz_zip ( a ):
	import os, pytz, zipfile, glob
	
	# hack a.scripts to include our runtime hook
	pytz_zip_hook = os.path.join ( os.path.dirname(__file__), 'pytz_zip_hook.py' )
	a.scripts.insert ( 0, ( 'pytz_zip_hook', pytz_zip_hook, 'PYSOURCE' ) )
	
	# remove all the timezone files from being included raw
	a.datas = [ (x,y,z) for x,y,z in a.datas if x[:5].rstrip('/\\') != 'pytz' ]
	
	# remove all pytz source files from a.pure because we want them loaded from our zip
	a.pure = [ (x,y,z) for x,y,z in a.pure if x[:5].rstrip('/\\') != 'pytz' ]
	
	# build our zip file...
	build_folder = os.path.dirname(a.tocfilename)
	zip_path = os.path.join ( build_folder, 'pytz.zip' )
	with zipfile.ZipFile(zip_path,'w') as zip:
		pytz_path = pytz.__path__[0]
		for root, dirs, files in os.walk(pytz_path):
			for file in files:
				file_path = os.path.join(root,file)
				arc_path = 'pytz/'+file_path[len(pytz_path):].lstrip('/\\')
				zip.write ( file_path, arc_path )
	
	# add our zip file to the compilation
	a.zipfiles.append ( ( 'pytz.zip', zip_path, '' ) )
