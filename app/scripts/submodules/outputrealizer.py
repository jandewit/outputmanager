#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.version import LooseVersion
import qi
import stk.services
import stk.events
import logging
import threading
import time
import re

class OutputRealizer:
        # https://stackoverflow.com/questions/9836425/equivelant-to-rindex-for-lists-in-python
        def listRightIndex(self, alist, value):
            return len(alist) - alist[-1::-1].index(value) -1        

	def __init__(self, outputmanager, qiapp = None, nao_ip = None):
		self.output = None
		self.is_interrupted = False
		self.last_known_child_location = None
		self.outputmanager = outputmanager
		self.is_face_tracking = False
		self.robot_volume_enabled = False
		self.variables = {}
		if qiapp != None:
			self.qiapp = qiapp
		else:
			qi_url = "192.168.100.110"
			if nao_ip != None:
				qi_url = nao_ip
			if qi_url.find(':') == -1:
				qi_url += ':9559' # Default port
			self.qiapp = qi.Application(url="tcp://"+qi_url)
			self.qiapp.start()
		self.s = stk.services.ServiceCache(self.qiapp.session)
		self.events = stk.events.EventHelper(self.qiapp.session)		
		self.s.ALAnimatedSpeech.setBodyLanguageMode(0)
		# Turn off the volume for the tablet condition, just in case something goes wrong with rerouting.
		self.toggle_robot_volume(False)
		# Disable some basic awareness
		try:
			self.s.ALBasicAwareness.setStimulusDetectionEnabled("Sound", False)
			self.s.ALBasicAwareness.setStimulusDetectionEnabled("Movement", False)
			self.s.ALBasicAwareness.setStimulusDetectionEnabled("Touch", False)
			self.s.ALBasicAwareness.setStimulusDetectionEnabled("People", False)
		except:
			pass
		self._toggle_facetracking_callback(False)
		self.s.ALRobotPosture.goToPosture("Crouch",0.5)
		self.s.ALLeds.on('AllLeds')
		# Go to crouching position and disable stiffness in legs
		names  = ['RKneePitch', 'LKneePitch','RAnklePitch','LAnklePitch','RAnkleRoll','LAnkleRoll']
		stiffnesses  = 0.0
		self.s.ALMotion.setStiffnesses(names,stiffnesses)
		self.lock = threading.Lock()
		self.events.subscribe("toggle_tablet", "OutputRealizer", self.outputmanager.tablet_screen_callback)
		self.events.subscribe("toggle_facetracking", "OutputRealizer", self._toggle_facetracking_callback)
		self.events.subscribe("trigger_facial_expression", "OutputRealizer", self._trigger_facial_expression)
		self.events.subscribe("accept_answer", "OutputRealizer", self.outputmanager.accept_answer_callback)
		self.events.subscribe("move", "OutputRealizer", self.outputmanager.move_object_callback)
		self.s.ALBehaviorManager.behaviorStopped.connect(self._behavior_stopped)
		self.om_sensor_touch_callback = self.outputmanager.sensor_touched_callback

	def _behavior_stopped(self, behaviorName):
		if self.is_face_tracking and "iconics/" in behaviorName:
			self._toggle_facetracking_callback('False')
			threading.Timer(2, self.reset_gaze, []).start()


	def update_for_condition(self):
		if self.outputmanager.is_tablet_condition:
			self.s.ALLeds.off('AllLeds')
			self.s.ALMotion.stiffnessInterpolation("Body", 0, 0.3)
			try:
				self.s.ALBehaviorManager.stopBehavior("custom/blinking")		
			except:
				pass
		else:
			# Turn on the volume.
			self.toggle_robot_volume(True)
        	        # Breathing: we don't enable head since we change gaze so much
			self.s.ALMotion.setBreathEnabled("Arms", True)
			# Blinking behaviour
			try:
				self.s.ALBehaviorManager.startBehavior("custom/blinking")
			except:
				pass	

	def sensor_touched_callback(self, params):
		if params[0][1] == True:			
			arm = None
			# Something wrong with the particular sensor LHand/Touch/Left being triggered
			if params[0][0] == "LArm" and params[1][0] != "LHand/Touch/Left":
				arm = "lefthand"
			elif params[0][0] == "RArm":
				arm = "righthand"
			if arm != None:
				self.om_sensor_touch_callback(arm)

	def toggle_touch_sensors(self, enabled):
		# This is a work-around to detect touch events on the robot hands, not really "output"
		if enabled:
			self.events.subscribe("TouchChanged", "OutputRealizer", self.sensor_touched_callback)
		else:
			self.events.disconnect("TouchChanged")

	def toggle_breathing(self, enabled):
		if enabled:
			self.s.ALMotion.setBreathEnabled("Arms", True)
			self._toggle_facetracking_callback(True)
		else:
			self.s.ALMotion.setBreathEnabled("Arms", False)
			self._toggle_facetracking_callback(False)


	def toggle_robot_volume(self, is_enabled):
		try:
			if is_enabled:
				self.s.ALAudioDevice.setOutputVolume(60)		
				self.robot_volume_enabled = True
			else:
				self.s.ALAudioDevice.setOutputVolume(0)						
				self.robot_volume_enabled = False
		except:
			pass

	def _trigger_facial_expression(self, expression):
		if expression == 'happy' and not self.outputmanager.is_tablet_condition:
			self.s.ALLeds.rasta(2)

	def _follow_face(self):
		try:
			self.s.ALFaceTracker.startTracker()
		except:
			pass
		initial_value = self.s.ALMotion.getAngles("Head", False)
		try:
			while self.s.ALFaceTracker.isActive():
				if self.s.ALFaceTracker.isNewData():				
					loc = self.s.ALMotion.getAngles("Head", False)

					if loc[0] != initial_value[0] and loc[1] != initial_value[1] and (self.last_known_child_location == None or (loc[0] != self.last_known_child_location[0] and loc[1] != self.last_known_child_location[1])):
						self.last_known_child_location = loc
				time.sleep(0.5)
		except:
			pass

	def _toggle_facetracking_callback(self, value):
		if value == 'True':
			if self.last_known_child_location == None:
				# Moving to default expected child location (first time only)
				self.s.ALMotion.angleInterpolationWithSpeed("Head", [0.704064, 0.0199001], 0.2)
			else:
				# Moving to the last known child location based on previous face tracking
				self.s.ALMotion.angleInterpolationWithSpeed("Head", self.last_known_child_location, 0.2)
			t = threading.Thread(target=self._follow_face)
			t.start()
			self.is_face_tracking = True
		else:		
			try:	
				self.s.ALFaceTracker.stopTracker()
			except:
				pass
			self.is_face_tracking = False

	def run_behavior(self, behavior_id):
		self.s.ALBehaviorManager.runBehavior(behavior_id)

	def start_behavior(self, behavior_id):
		try:
			self.s.ALBehaviorManager.startBehavior(behavior_id)
			self.outputmanager.log_to_memory('gesture', {
				'is_iconic': False,
				'id': behavior_id
			})			
		except:
			pass

	def set_gaze(self, target):
		try:
			if target == 'child':
				self._toggle_facetracking_callback('True')
			else:
				self.s.ALBehaviorManager.runBehavior('gaze/tablet')
		except:
			pass

	def reset_gaze(self):
		logging.debug("Resetting child location for gaze")
		self._toggle_facetracking_callback('False')
		self.last_known_child_location = None
		self._toggle_facetracking_callback('True')


	def set_variable(self, key, value):
		self.variables[key] = value

	def _get_speech_tags_for_lang(self, lang_code):
		if lang_code == 'English':
			return '\\rspd=75\\ \\vct=110\\ \\vol=100\\ '
		elif lang_code == 'Dutch':
			return '\\rspd=80\\ \\vct=100\\ \\vol=70\\ '
		else:
			return '' # @TODO: implement German and Turkish parameters

	def set_languages(self, l1, l2):
		self.l1 = l1
		self.l2 = l2
		# Set correct speech parameters (pitch, volume)
		self.l1_speech_tags = self._get_speech_tags_for_lang(self.l1)
		self.l2_speech_tags = self._get_speech_tags_for_lang(self.l2)
		self.s.ALTextToSpeech.setLanguage(self.l1)

	def say(self, text):
		self.lock.acquire()
		self.is_interrupted = False
		tag_pattern = re.compile('<([a-zA-Z0-9_(),.\- ]+)>')
		l2_pattern = re.compile('{([a-zA-Z0-9_() ]+)}')		
		last_gaze = None
		postfix = ""
		added_wait_pointing = False
		text_notags = text
		# Convert tags into commands for AnimatedSpeech
		for r in tag_pattern.finditer(text):
			s = r.group(1).lower()
			text_notags = text_notags.replace('<' + r.group(1) + '>', '')
			if s.startswith('tablet'):
				command = r.group(1)
				# Tablet needs to be timed with the output, so we use ALMemory to call back to a function.. :D
				text = text.replace('<' + command + '>', ' $toggle_tablet=' + command[command.find('(')+1:command.find(')')] + ' ')
			elif s.startswith('move'):
				command = r.group(1)
				param = command[command.find('(')+1:command.find(')')].replace(' ', '')
				text = text.replace('<' + command + '>', ' $move=' + param + ' ')
			elif s.startswith('face'):
				# facial expressions (LED)
				command = r.group(1)
				expression = command[command.find('(')+1:command.find(')')].lower()
				expression = expression.replace(' ', '_')
				if self.outputmanager.is_tablet_condition:
					text = text.replace('<' + r.group(1) + '>', '')
				else:
					text = text.replace('<' + r.group(1) + '>', ' $trigger_facial_expression=' + expression + ' ')
			elif s.startswith('gaze'):
				command = r.group(1)
				direction = command[command.find('(')+1:command.find(')')].lower()
				if direction == 'child':
					target = ' $toggle_facetracking=True '
				else:
					target = ' $toggle_facetracking=False ^start(gaze/' + command[command.find('(')+1:command.find(')')].lower() + ') '
					if not self.outputmanager.is_tablet_condition and last_gaze != None:
						target = '^wait(' + last_gaze + ') ' + target
					last_gaze = 'gaze/' + command[command.find('(')+1:command.find(')')].lower()
				if self.outputmanager.is_tablet_condition:					
					text = text.replace('<' + r.group(1) + '>', '')		
				else:
					text = text.replace('<' + r.group(1) + '>', target)		
			elif s.startswith('pointat'):
				command = r.group(1)
				direction = command[command.find('(')+1:command.find(')')].lower()
				output = ''
				if direction == 'tablet':
					output = ' ^start(pointing/tablet) '
					if not self.outputmanager.is_tablet_condition and not added_wait_pointing:
						text = text + ' ^wait(pointing/tablet)'
						added_wait_pointing = True
				# For now we have static pointing
				if self.outputmanager.is_tablet_condition:
					text = text.replace('<' + r.group(1) + '>', '')
				else:
					text = text.replace('<' + r.group(1) + '>', output)
					self.outputmanager.log_to_memory('gesture', {
						'is_iconic': False,
						'id': 'pointing/tablet'
					})
			elif s.startswith('gesture'):
				# @TODO: play back gesture
				command = r.group(1)
				gesture = command[command.find('(')+1:command.find(')')].lower().replace(' ', '_')
				output = ''
				# For now we will use pointing also for pretending to touch tablet
				if not self.outputmanager.is_tablet_condition and gesture == 'pretends_to_touch_tablet':
					output = ' ^start(pointing/tablet) '
					self.outputmanager.log_to_memory('gesture', {
						'is_iconic': False,
						'id': 'pointing/tablet'
					})					
					if not added_wait_pointing:
						text = text + ' ^wait(pointing/tablet)'
						added_wait_pointing = True
				elif not self.outputmanager.is_tablet_condition and gesture == 'touch':
					output = ' ^start(touch/tablet) '
					postfix += ' ^wait(touch/tablet) '

					self.outputmanager.log_to_memory('gesture', {
						'is_iconic': False,
						'id': 'touch/tablet'
					})					
				if self.outputmanager.is_tablet_condition:                                               
					text = text.replace('<' + r.group(1) + '>', '')
				else:
					text = text.replace('<' + r.group(1) + '>', output) # @TODO: replace with smart tag to start behavior
			elif s.replace(' ', '_').strip() == 'accept_answer':
				text = text.replace('<' + r.group(1) + '>', ' $accept_answer=True ')
			else: # Must be a variable..
				replacement = ''
				if self.variables.has_key(r.group(1)):
					replacement = self.variables[r.group(1)]
				text = text.replace('<' + r.group(1) + '>', replacement)
		if not self.outputmanager.is_tablet_condition and last_gaze != None:
			text += '^wait(' + last_gaze + ')'
		text += postfix
		# List will contain separate entries for L1 and L2 utterances
		to_say_parts = list()
		l2s = [r.start() for r in re.finditer('{', text)]
		if len(l2s) == 0:
			to_say_parts.append({
				'text': text,
				'l2': False
			})
		else:
			prev_index = 0
			for l2 in l2s:
				end_index = text.find('}', l2)
				to_say_parts.append({
					'text': text[prev_index:l2],
					'l2': False
				})
				to_say_parts.append({
					'text': text[l2+1:end_index],
					'l2': True
				})
				prev_index = end_index+1

			to_say_parts.append({
					'text': text[prev_index:],
					'l2': False
				})
		logging.info(text.encode('utf8'))
		# Some corrections needed for when stuff like comma is recognized as a word..
		text_notags = text_notags.replace(',', '').replace('.', '')
		segments = text_notags.split()
		self.current_utterance_length = len(segments)
		self.current_utterance_index = 0
                pau_dict = { #should be loaded from somewhere else
                        "one":"\\pau=1500\\",
                        "two":"\\pau=1500\\",
                        "three":"\\pau=1500\\",
                        "more":"\\pau=2000\\",
                        "add":"\\pau=3500\\",
                        "most":"\\pau=2500\\",
                        
                        "take away":"\\pau=3000\\",
                        "four":"\\pau=2000\\",
                        "five":"\\pau=2200\\",
                        "fewer":"\\pau=2500\\",
                        "fewest":"\\pau=3500\\",
                        
                        "big":"\\pau=2500\\",
                        "small":"\\pau=1500\\",
                        "heavy":"\\pau=2500\\",
                        "light":"\\pau=2500\\",
                        "high":"\\pau=2000\\",
                        "low":"\\pau=2000\\",
                        
                        "on":"\\pau=2000\\",
                        "above":"\\pau=2500\\",
                        "below":"\\pau=2000\\",
                        "next to":"\\pau=1750\\",
                        "falling":"\\pau=2000\\",
                        
                        "in front of":"\\pau=1750\\",
                        "behind":"\\pau=1500\\",
                        "walking":"\\pau=3000\\",
                        "running":"\\pau=2000\\",
                        "jumping":"\\pau=2000\\",
                        "flying":"\\pau=3000\\",
                        
                        "left":"\\pau=1500\\",
                        "right":"\\pau=1500\\",
                        "catching":"\\pau=1500\\",
                        "throwing":"\\pau=1000\\",
                        "sliding":"\\pau=2000\\",
                        "climbing":"\\pau=3000\\"
                        
                }                
		# Actually do the utterance
		# fasten your seatbelts..
		for part in to_say_parts:
			if not self.is_interrupted:
				if part['l2']:
					if self.l2 == 'Turkish':
						self.s.ALAnimatedSpeech.say(' ^runSound(Tudu/' + part['text'].lower().replace('.', '').replace('!', '').replace(' ', '').encode('ascii', 'ignore') + ')')
					else:
						if self.outputmanager.is_gesture_condition == True and self.outputmanager.is_test == False:
							#one of these works
							targets = ["\\\\\\rspd=50\\\\\\add\\\\\\rspd=75\\\\\\", "\\\\rspd=50\\\\add\\\\rspd=75\\\\", "\\rspd=50\\add\\rspd=75\\",
                                                                   'one', 'two', 'three', 'more', 'add', 'most', 'four', 'five', 'fewer', 'take away', 'fewest', 'big', 'small',
                                                                   'heavy', 'light', 'high', 'low', 'on', 'above', 'below', 'next to', 'falling', 'in front of', 'behind', 'walking',
                                                                   'running', 'jumping', 'flying', 'left', 'right', 'catching', 'throwing', 'sliding', 'climbing']
							targets_split = list()
							for target in targets:
								targets_split.append(target.split(' '))
							target_found = ''
							multiple_targets_found_list = list()
							str_parts = str(part['text']).split(' ')
							for s_i in range(0, len(str_parts)):
                                                                str_part = str_parts[s_i]                                                              
                                                                str_part = str_part.lower().replace('.', '').replace(',', '').replace('!', '').replace('?', '')                                                                
                                                                for target in targets_split: # does not solve for multiple targets in same utterance
                                                                        for element in target:
                                                                                if element == str_part:
                                                                                        str_parts[s_i] = str_part
                                                                                        if element in ["\\\\\\rspd=50\\\\\\add\\\\\\rspd=75\\\\\\", "\\\\rspd=50\\\\add\\\\rspd=75\\\\", "\\rspd=50\\add\\rspd=75\\", ['\\\\rspd=50\\\\add\\\\rspd=75\\\\'], ['\\rspd=50\\add\\rspd=75\\'], ['\\\\\\rspd=50\\\\\\add\\\\\\rspd=75\\\\\\']]:
                                                                                                target_found = ['add']
                                                                                                index_add = element # this might fix the add problem, look for this with .index()
                                                                                                if not target_found in multiple_targets_found_list:
                                                                                                        multiple_targets_found_list.append(target_found)                                                                                                
                                                                                        else: #hardcoding solution for targets that are multiple words
                                                                                                if element in ["in", ["in"]]:
                                                                                                        pass
                                                                                                elif element in ["front", ["front"]]:
                                                                                                        pass
                                                                                                elif element in ["take", ["take"]]:
                                                                                                        pass
                                                                                                elif element in ["next", ["next"]]:
                                                                                                        pass  
                                                                                                else:
                                                                                                        if element == "of" and (s_i < 2 or str_parts[s_i-1] != "front" or str_parts[s_i-2] != "in"):
                                                                                                                pass
                                                                                                        elif element == "away" and (s_i < 1 or str_parts[s_i-1] != "take"):
                                                                                                                pass
                                                                                                        elif element == "to" and (s_i < 1 or str_parts[s_i-1] != "next"):
                                                                                                                pass
                                                                                                        else:
                                                                                                                target_found = target
                                                                                                                if not target_found in multiple_targets_found_list:
                                                                                                                        multiple_targets_found_list.append(target_found)
                                                                                else:
                                                                                        pass
							part['text'] = ' '.join(str_parts)
							if len(multiple_targets_found_list) < 2: #also need to do exception for add here
								if target_found == ['add'] or target_found == 'add':
                                                                        try:
                                                                                pause = pau_dict[" ".join(target_found)] #something is broken here
                                                                        except Exception as e:
                                                                                pass
                                                                        try:
                                                                                part_text = str(part['text']).split(' ')
                                                                                part_text.insert(self.listRightIndex(part_text, index_add)+1, pause)
                                                                                part['text'] = ' '.join(part_text)
                                                                        except Exception as e:
                                                                                pass
                                                                        target = '_'.join(target_found)
                                                                        try:
                                                                                self.s.ALBehaviorManager.startBehavior("iconics/" + target)
                                                                                self.outputmanager.log_to_memory('gesture', {
                                                                                        'is_iconic': True,
                                                                                        'id': 'iconics/' + target
                                                                                })									
                                                                        except Exception as e:
                                                                                pass                                                                        
								else:
                                                                        try:
                                                                                pause = pau_dict[" ".join(target_found)] #something is broken here
                                                                        except Exception as e:
                                                                                pass
                                                                        try:
                                                                                part_text = str(part['text']).split(' ')
                                                                                part_text.insert(self.listRightIndex(part_text, target_found[-1])+1, pause)
                                                                                part['text'] = ' '.join(part_text)
                                                                        except Exception as e:
                                                                                pass
                                                                        target = '_'.join(target_found)
                                                                        try:                                                                                
                                                                                self.s.ALBehaviorManager.startBehavior("iconics/" + target)
                                                                                self.outputmanager.log_to_memory('gesture', {
                                                                                        'is_iconic': True,
                                                                                        'id': 'iconics/' + target
                                                                                })									
                                                                        except Exception as e:
                                                                                pass                                                   
								self.s.ALTextToSpeech.say(self.l2_speech_tags + part['text'], self.l2)
							else: # this does not yet work for the weird \\ add stuff
								target_gestures = list()
								for targets_found in multiple_targets_found_list: #target = targets
                                                                        if targets_found == ['add'] or targets_found == 'add':  # this did the trick for the weird \\ add stuff
                                                                                try:
                                                                                        pause = pau_dict[" ".join(targets_found)]
                                                                                except Exception as e:
                                                                                        pass
                                                                                try:
                                                                                        part_text = str(part['text']).split(' ')
                                                                                        part_text.insert(self.listRightIndex(part_text, index_add)+1, pause)
                                                                                        delim = "-:-"
                                                                                        part_text.insert(self.listRightIndex(part_text, index_add)+2, delim)
                                                                                        part['text'] = ' '.join(part_text)
                                                                                except Exception as e:
                                                                                        pass                                          
                                                                                target = '_'.join(targets_found)
                                                                                target_gestures.append(target)
                                                                        else:
                                                                                try:
                                                                                        pause = pau_dict[" ".join(targets_found)] #something is broken here
                                                                                except Exception as e:
                                                                                        pass
                                                                                try:
                                                                                        part_text = str(part['text']).split(' ')
                                                                                        part_text.insert(self.listRightIndex(part_text, targets_found[-1])+1, pause)
                                                                                        delim = "-:-"
                                                                                        part_text.insert(self.listRightIndex(part_text, targets_found[-1])+2, delim)
                                                                                        part['text'] = ' '.join(part_text)
                                                                                except Exception as e:
                                                                                        pass                                                    
                                                                                target = '_'.join(targets_found)
                                                                                target_gestures.append(target)
								parts_to_say = part['text'].split("-:-")
								count = 0
								for ting in parts_to_say:
									try:
										target = target_gestures[count]
										self.s.ALBehaviorManager.startBehavior("iconics/" + target)
										count += 1
										self.outputmanager.log_to_memory('gesture', {
											'is_iconic': True,
											'id': 'iconics/' + target
										})										                                                                                
									except Exception as e:
										pass                                           
                                                                        self.s.ALTextToSpeech.say(self.l2_speech_tags + ting, self.l2)
						else:
							self.s.ALTextToSpeech.say(self.l2_speech_tags + part['text'], self.l2)
				else:
					self.s.ALAnimatedSpeech.say(self.l1_speech_tags + part['text'])
		# If we got interrupted, we still need to send output_completed
		logging.debug("Output completed")
		self.lock.release()

	def interrupt_output(self, give_instruction = False):
		logging.debug("Interrupt output")
		self.is_interrupted = True
		self.s.ALTextToSpeech.stopAll()
		self.s.ALBehaviorManager.stopAllBehaviors()
		if not self.outputmanager.is_tablet_condition:
			# Restarting the blinking, maybe we should do this in a nicer way
			try:
				self.s.ALBehaviorManager.startBehavior("custom/blinking")
			except:
				pass
		if give_instruction:
			self.s.ALTextToSpeech.say("Please let me finish")
		# We don't send output completed here because the original output completed will trigger
	def clean_up(self):
		# self.s is no longer available in the destructor
		try:
			if self.s.ALFaceTracker.isActive():
				self.s.ALFaceTracker.stopTracker()
			self.s.ALMotion.setBreathEnabled("Arms", False)		
			self.s.ALBehaviorManager.stopBehavior("custom/blinking")
		except:
			pass

	def __del__(self):
		self.qiapp.stop()
