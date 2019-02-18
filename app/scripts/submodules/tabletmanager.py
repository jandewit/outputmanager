import os.path
import pyaudio
import wave
import time

class TabletManager:

	def __init__(self, outputmanager):
		self.outputmanager = outputmanager
		
	def set_languages(self, l1, l2):
		self.l1 = l1
		self.l2 = l2

	def say(self, text):
		if self.outputmanager.is_tablet_condition:
			time.sleep(1.5)
		# @TODO: find the proper file in some look-up table and play it
		# @TODO: check for <> and figure out what to do with special cases such as happy_sound. For now we just remove
		to_say = text.lower().strip().replace('<', '').replace('>', '').replace(' ', '_').replace('.', '').replace(',', '')
		filename = os.path.join(os.path.dirname(__file__), 'tablet_outputs/' + self.l2.lower() + '/' + to_say + '.wav')
		print 'Tablet output: ' + filename
		#define stream chunk   
		chunk = 1024  
		#open a wav format music
		try:  
			f = wave.open(filename,"rb")  
			#instantiate PyAudio  
			p = pyaudio.PyAudio()  
			#open stream  
			stream = p.open(format = p.get_format_from_width(f.getsampwidth()),  
			                channels = f.getnchannels(),  
			                rate = f.getframerate(),  
			                output = True)  
			#read data  
			data = f.readframes(chunk)  
			#play stream  
			while data:  
			    stream.write(data)  
			    data = f.readframes(chunk)  
			#stop stream  
			stream.stop_stream()  
			stream.close()
			#close PyAudio  
			p.terminate()
		except:
			pass
			
		print "=== PLAYBACK COMPLETED ==="	

		# Tablet shouldn't send output completed because it will be linked to giving feedback, thereby triggering 2 output completed..
		#self.output_completed_callback()
		# moveObject(JSON(id, position: { x, y, z }, timeout))
		# timeout is in seconds
