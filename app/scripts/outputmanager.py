#!/usr/bin/env python
# -*- coding: utf-8 -*-

from submodules.outputrealizer import OutputRealizer
from submodules.feedbackmanager import FeedbackManager
from submodules.tabletmanager import TabletManager
from submodules.tabletconditionmanager import TabletConditionManager

import logging
import log_formatter as lf
import socket
import threading
import time
import json
import re
import os.path
from optparse import OptionParser
from Queue import Queue, Empty

runningReading = True

class OutputManager:

	def load_session(self, session_id):
		if self.loadedSession == None or self.loadedSession != session_id:
			# Load the correct session file
			with open(os.path.join(os.path.dirname(__file__), '../../../datamodel/sessions/outputmanager/' + session_id)) as infile:
				self.output = json.load(infile)
				self.loadedSession = session_id
				logging.debug("Loaded session file: " + session_id)

	def _find_if_l2(self, text):		
		text = text.lower()
		if text == "":
			# This is a work-around for L1+L2 mixed queries, where we don't want the robot to speak in L2 only..
			return False
		existing = self._get_output_for_task(self.latest_task)
		existing_output = None
		for out in existing:
			if out['type'] == 'TEXT_OUTPUT':
				existing_output = out
				break		
		if existing_output != None:
			l2_pattern = re.compile('{([a-zA-Z0-9_()? ]+)}')
			existing_output_strip = existing_output['text'][self.l1].replace("<accept_answer>", "").replace("\\", "").replace("=", "").strip()
			if len(existing_output_strip) == 0:
				return False
			for r in l2_pattern.finditer(existing_output_strip):
				s = r.group(1).lower()
				if s.find(text) != -1:
					self.prev_l2[text] = True
					return True
			if existing_output_strip[0] == '{' and existing_output_strip.find('}', 1) == len(existing_output_strip)-1:
				if text in self.prev_l2:
					return self.prev_l2[text]
				else:
					return False
		self.prev_l2[text] = False
		return False

	def _check_and_run_tablet_output(self):
		# If we have a tablet utterance, this needs to come first (as feedback to a click)
		to_do = self._get_output_for_task(self.latest_task)
		for out in to_do:
			if out['type'] == 'TABLET_SPEECH_OUTPUT':
				self.tabletmanager.say(out['text'])
				print "======> SENDING MESSAGAGE COMPLETED: TABLET_OUTPUT"
				self.sendMessage(self.sock, "call:tablet.interactionmanager.tablet_output_completed")

	def _get_output_for_task(self, json_params):
		task_id = json_params['task']
		subtask_id = json_params['subtask']
		difficulty = json_params['difficulty'] # This might be optional?
		return self.output[str(task_id).zfill(3) + ':' + str(subtask_id).zfill(3)]

	def _extract_l2_targets(self, text):
                # add is a mess, we'll fix it like this
		targets = ["\\\\\\rspd=50\\\\\\add\\\\\\rspd=75\\\\\\",
                           "\\\\rspd=50\\\\add\\\\rspd=75\\\\",
                           "\\rspd=50\\add\\rspd=75\\", 'one', 'two',
                           'three', 'more', 'add', 'most', 'four', 'five',
                           'fewer', 'take away', 'fewest', 'big', 'small',
                           'heavy', 'light', 'high', 'low', 'on', 'above',
                           'below', 'next to', 'falling', 'in front of',
                           'behind', 'walking', 'running', 'jumping',
                           'flying', 'left', 'right', 'catching',
                           'throwing', 'sliding', 'climbing']
		text = text.replace('\\', '').replace('rspd=50', '').replace('rspd=75', '')
		l2_pattern = re.compile('{([a-zA-Z0-9_(),.\-\' ]+)}')		
		res = list()
		for r in l2_pattern.finditer(text):
			s = r.group(1).lower()
			for t in targets:
				m = re.compile(r'\b%s\b' % t, re.I)
				if m.search(s) != None:
					res.append(t)
		return res

	def _is_numeric(self, char):
		try:
			float(char)
			return True
		except ValueError:
			return False

	def _obj_json_to_string(self, obj_json, include_article = True):
		singular_plural = 'singular'
		lang = self.l1
		obj_id = obj_json['id']
		print "====== " + obj_id[obj_id.rfind('_')+1]
		if obj_id.rfind('_') != -1 and self._is_numeric(obj_id[obj_id.rfind('_')+1]):
			obj_id = obj_id[:obj_id.rfind('_')]	
		obj_id = obj_id.replace('_', ' ')
		# Check if plural
		if 'is_plural' in obj_json and obj_json['is_plural']:
			singular_plural = 'plural'
		# Check if the target word is originally referenced in L2 in the utterance
		if self._find_if_l2(self.dict[obj_id][self.l2][singular_plural]['text']):
			lang = self.l2
		if include_article:
			art = self.dict[obj_id][lang][singular_plural]['article']
			# This was an exception for the pilot Eng -> Ger
			if lang == self.l2 and self.l2 == 'German':
				art = 'the'
			output = art + ' ' + self.dict[obj_id][lang][singular_plural]['text']
		else:
			output = self.dict[obj_id][lang][singular_plural]['text']
		if lang == self.l2:
			output = '{' + output + '}'
		return output

	def log_to_memory(self, category, structure):
		structure['timestamp'] = time.time()
		data = {
			"key": category,
			"data": structure
		}
		self.sendMessage(self.sock, "call:tablet.interactionmanager.log_output_information|%s" % (json.dumps(data)))	

	def reset_gaze(self, dummy_param):
		self.outputrealizer.reset_gaze()

	# Introduce a task (could also be an introduction)
	# I think we can only send one parameter through ConnectionManager, so we'd have to parse it.
	def give_task(self, params):
		while self.wait_tabletcondition:
			time.sleep(0.1)
		self.count_req = 0
		self.feedbackmanager.count_fb = 0
		json_params = json.loads(params)
		logging.debug("Give task: " + str(json_params['task']) + ', subtask ' + str(json_params['subtask']) + ', difficulty ' + str(json_params['difficulty']))
		if 'is_test' in json_params:
			self.is_test = json_params['is_test']
			print self.is_test
		self.latest_task = json_params
		to_do = self._get_output_for_task(json_params)
		if json_params['type'] == 'SENSOR_TOUCH_CRITERIUM':
			self.outputrealizer.toggle_touch_sensors(True)
		# If no feedback will happen, we do the tablet output already.
		if json_params['type'] == 'RESPONSE_DELAY_CRITERIUM' or json_params['type'] == 'OUTPUT_FINISH_CRITERIUM':
			self._check_and_run_tablet_output()
		for out in to_do:
			if out['type'] == 'TEXT_OUTPUT':
				self.outputrealizer.say(out['text'][self.l1])
				print "======> SENDING MESSAGAGE COMPLETED: GIVE_TASK"
				self.sendMessage(self.sock, "call:tablet.interactionmanager.give_task_completed")
			elif out['type'] == 'TABLET_SPEECH_OUTPUT':
				pass # We moved this to take place before feedback				

	# Feedback function
	# @TODO: would like to name this give_feedback instead but ConnectionManager seems to cut off messages at _
	def give_feedback(self, params):
		# Params: {"valid": False, "answer": True, "type": "VOICE_ACTIVATION_CRITERIUM", "ADD_INFO": "some task related information"}
		json_params = json.loads(params)
		# Retrieve feedback to give from the feedbackmanager -- this might in the end be a bit more complex
		# and contain both verbal as well as nonverbal utterances?
		self.feedback = self.feedbackmanager.get_feedback(json_params)
		feedback = {
			'positive': {
				'English': 'Well done!',
				'Dutch': 'Goedzo!',
				'German': 'Sehr gut'
			},
			'negative': {
				'English': 'That\'s not quite right',
				'Dutch': 'Dat klopt niet helemaal',
				'German': 'Nicht ganz richtig'
			}
		}
		# @TODO: send feedback to self.outputrealizer to actually create output?
		if json_params['valid']:
			self._check_and_run_tablet_output()
			self.outputrealizer.say(self.feedback)
			print params
			current_task_output = self._get_output_for_task(self.latest_task)
			for cto in current_task_output:
				if cto['type'] == 'TEXT_OUTPUT':
					objective = cto['objective']
					break			
			# Sanity check, should never happen though
			if objective == None:
				return			
			if json_params['type'] == 'OBJECT_COLLISION_CRITERIUM':
				data = {
					'obj_1': json_params["ADD_INFO"]["obj_1"],
					'obj_2': json_params["ADD_INFO"]["obj_2"]
				}
				if 'disappear' in objective:
					data['disappear'] = objective['disappear']
					if not objective['disappear']:
						data['target_location'] = objective['target_location']
				else:
					data['disappear'] = True
				self.sendMessage(self.sock, "call:tablet.WebSocket.showCollisionFeedback|%s" % (json.dumps(data)))
				time.sleep(2.5)
			if json_params['type'] == 'SENSOR_TOUCH_CRITERIUM':
				print "==== CORRECT STUFF ==="
				self.outputrealizer.toggle_touch_sensors(False)
                        print "======> SENDING MESSAGAGE COMPLETED: FEEDBACK"
			self.sendMessage(self.sock, "call:tablet.interactionmanager.feedback_completed")
		else:
			self.outputrealizer.say(self.feedback)
                        print "======> SENDING MESSAGAGE COMPLETED: FEEDBACK"
			self.sendMessage(self.sock, "call:tablet.interactionmanager.feedback_completed")

	def give_break(self, break_activity_id):
		# @TODO: implement me
		pass

	def resume_interaction(self):
		# @TODO: implement me
		pass

	def request_answer(self, params):
		# @TODO: fix the utterances: multi-lingual, maybe more variation / scaffolding, add child's name only if attention is low?
		logging.debug("Request answer")
		# @TODO: there is a variation in the script of Utrecht in some cases, do we want to randomly pick one?
		# Example, for touching objects:
		# 1. Do you see the zoo? Touch it on the tablet!
		# 2. Touch the zoo on the tablet!
		#
		# And for speech:
		# 1. Say "zoo"
		# 2. I know you can do it, say it just like I do: "zoo"
		speech_content = {
			'OBJECT_SELECT_CRITERIUM': {
				'English': 'Touch [obj_id] on the tablet',
				'Dutch': 'Raak [obj_id] maar aan op de \prn=t E: b l @ t \\',
				'German': ''
			},
			'VOICE_ACTIVATION_CRITERIUM': {
				'English': 'Say: [target]',
				'Dutch': 'Zeg maar: [target]',
				'German': '',
			},
			'OBJECT_MOVE_CRITERIUM': {
				'English': 'Let\'s put [obj_1] [rel] [obj_2]',
				'Dutch': 'Laten we, [obj_1] [rel] [obj_2] zetten',
				'German': ''
			},
			'OBJECT_MOVE_CRITERIUM_2D': {
				'English': 'Let\'s put [obj_1] [rel] [obj_2]',
				'Dutch': 'Laten we, [obj_1] op [obj_2] plakken',
				'German': ''
			},
			'OBJECT_COLLISION_CRITERIUM': {
				'English': 'Let\'s put [obj_1] in [obj_2]',
				'Dutch': 'Laten we, [obj_1] in [obj_2] doen',
				'German': ''
			},
			'SENSOR_TOUCH_CRITERIUM': {
				'English': 'Touch my [obj_1]',
				'Dutch': 'Raak mijnn [obj_1] maar aan',
				'German': ''
			}
		}
		relations = {
			'in': {
				'English': 'in',
				'Dutch': 'in',
				'German': 'in den'
			},
			'next_to': {
				'English': 'next to',
				'Dutch': 'naast',
				'German': 'neben den'
			},
			'next to': {
				'English': 'next to',
				'Dutch': 'naast',
				'German': 'neben den'
			},
			'most': {
				'English': 'most',
				'Dutch': 'de meeste',
				'German': 'den meisten'
			},
			'more': {
				'English': 'more',
				'Dutch': 'meer',
				'German': 'mehr'
			},
			'or': {
				'English': 'or',
				'Dutch': 'of',
				'German': 'oder'
			},
			'with': {
				'English': 'with',
				'Dutch': 'met',
				'German': 'mit'
			},
			'NOT_above': {
				'English': 'down from',
				'Dutch': 'van',
				'German': ''
			},
			'above': {
				'English': 'on',
				'Dutch': 'op',
				'German': ''
			}
		}
		json_params = json.loads(params)
		if json_params['type'].upper() == 'OBJECT_SELECT_CRITERIUM':
			to_say = speech_content['OBJECT_SELECT_CRITERIUM'][self.l1]
			# In case of an object select criterium, we now try to obtain the object from the current task description in JSON.
			current_task_output = self._get_output_for_task(self.latest_task)
			objective = None
			for cto in current_task_output:
				if cto['type'] == 'TEXT_OUTPUT':
					objective = cto['objective']
					break
			# Sanity check, should never happen though
			if objective == None:
				return
			target_obj = self._obj_json_to_string(objective)
			# Add a relation if it is there
			if 'rel' in objective:
				# The relation is with another object so we should also add that :)
				if objective['rel']['type'] == 'more' or objective['rel']['type'] == 'most' or objective['rel']['type'] not in relations:
					obj2 = self._obj_json_to_string(objective['rel']['target'], False)
					target_obj += ' ' + relations['with'][self.l1]
				else:
					obj2 = self._obj_json_to_string(objective['rel']['target'])
				to_find = objective['rel']['type']				
				if objective['rel']['type'] in relations:
					to_find = relations[objective['rel']['type']][self.l2]
				if self._find_if_l2(to_find):
					# Sometimes this can be a number, so we should check if the relation is known
					if objective['rel']['type'] in relations:
						target_obj += ' {' + relations[objective['rel']['type']][self.l2]
					else:
						target_obj += ' {' + self.dict[objective['rel']['type']][self.l2]['singular']['text']
					if obj2.startswith('{'):
						target_obj += ' ' + obj2[1:]
					else:
						target_obj += '} ' + obj2
				else:
					# Sometimes this can be a number, so we should check if the relation is known
					if objective['rel']['type'] in relations:
						target_obj += ' ' + relations[objective['rel']['type']][self.l1]					
					else:
						target_obj += ' ' + self.dict[objective['rel']['type']][self.l1]['singular']['text']
					target_obj += ' ' + obj2
				if 'opts' in objective:
					optstr = ''					
					i = 0
					while i < len(objective['opts']):
						opt = objective['opts'][i]
						if i == len(objective['opts']) - 1:
							optstr += ' ' + relations['or'][self.l1]
						elif i > 0 and i < len(objective['opts']) - 1:
							optstr += ', '
						optstr += ' ' + self._obj_json_to_string(opt)
						i += 1
					to_say += ': ' + optstr
			to_say = to_say.replace('[obj_id]', target_obj.encode('utf8'))
			self.log_to_memory("request_answer", {
				"request_count": self.count_req,
				"l2_exposures": self._extract_l2_targets(to_say)
			})
			if self.count_req > 0:
				to_say = "<name>, " + to_say
			self.count_req += 1
			self.outputrealizer.say(to_say)
			print "======> SENDING MESSAGAGE COMPLETED: REQUEST_ANSWER"
			self.sendMessage(self.sock, "call:tablet.interactionmanager.request_answer_completed")
		elif json_params['type'].upper() == 'VOICE_ACTIVATION_CRITERIUM':
			# We expect the word to be L2 and singular in all cases
			to_say = speech_content['VOICE_ACTIVATION_CRITERIUM'][self.l1]
			obj = self.dict[json_params['word']][self.l2]['singular']['text']
			to_say = to_say.replace('[target?]', '{' + obj.encode('utf8') + '?}')
			to_say = to_say.replace('[target]', '{' + obj.encode('utf8') + '}')
			self.log_to_memory("request_answer", {
				"request_count": self.count_req,
				"l2_exposures": self._extract_l2_targets(to_say)
			})
			if self.count_req > 0:
				to_say = "<name>, " + to_say
			self.count_req += 1
			self.outputrealizer.say(to_say)
			print "======> SENDING MESSAGAGE COMPLETED: REQUEST_ANSWER"
			self.sendMessage(self.sock, "call:tablet.interactionmanager.request_answer_completed")
		elif json_params['type'].upper() == 'OBJECT_MOVE_CRITERIUM' or json_params['type'].upper() == 'OBJECT_COLLISION_CRITERIUM' or json_params['type'] == 'OBJECT_MOVE_CRITERIUM_2D':	
			obj1_id = json_params['obj_1']
			if obj1_id.rfind('_') != -1 and self._is_numeric(obj1_id[obj1_id.rfind('_')+1]):
				obj1_id = obj1_id[:obj1_id.rfind('_')]	
			obj2_id = json_params['obj_2']
			if obj2_id.rfind('_') != -1 and self._is_numeric(obj2_id[obj2_id.rfind('_')+1]):
				obj2_id = obj2_id[:obj2_id.rfind('_')]	
			to_say = speech_content[json_params['type'].upper()][self.l1]
			# For now, we assume a move action is always moving 1 item next to 1 other item (all singular)
			if self._find_if_l2(self.dict[obj1_id][self.l2]['singular']['text']):
				obj1 = self.dict[obj1_id][self.l2]['singular']['text']
				if self.l2 != 'German' and self.dict[obj1_id][self.l2]['singular']['article'] != '':
					obj1 = self.dict[obj1_id][self.l2]['singular']['article'] + ' ' + obj1
				if self.l2 == 'German':
					to_say = to_say.replace('[obj_1?]', 'the {' + obj1.encode('utf8') + '?}')
					to_say = to_say.replace('[obj_1]', 'the {' + obj1.encode('utf8') + '}')
				else:
					to_say = to_say.replace('[obj_1?]', '{' + obj1.encode('utf8') + '?}')
					to_say = to_say.replace('[obj_1]', '{' + obj1.encode('utf8') + '}')
			else:
				obj1 = self.dict[obj1_id][self.l1]['singular']['text']
				if self.dict[obj1_id][self.l1]['singular']['article'] != '':
					obj1 = self.dict[obj1_id][self.l1]['singular']['article'] + ' ' + obj1
				to_say = to_say.replace('[obj_1?]', obj1.encode('utf8') + '?')
				to_say = to_say.replace('[obj_1]', obj1.encode('utf8'))
			if self._find_if_l2(self.dict[obj2_id][self.l2]['singular']['text']):
				obj2 = self.dict[obj2_id][self.l2]['singular']['text']
				if self.l2 != 'German' and self.dict[obj2_id][self.l2]['singular']['article'] != '':
					obj2 = self.dict[obj2_id][self.l2]['singular']['article'] + ' ' + obj2
				if self.l2 == 'German':
					to_say = to_say.replace('[obj_2?]', 'the {' + obj2.encode('utf8') + '?}')
					to_say = to_say.replace('[obj_2]', 'the {' + obj2.encode('utf8') + '}')
				else:
					to_say = to_say.replace('[obj_2?]', '{' + obj2.encode('utf8') + '?}')
					to_say = to_say.replace('[obj_2]', '{' + obj2.encode('utf8') + '}')
			else:
				obj2 = self.dict[obj2_id][self.l1]['singular']['text']
				if self.l1 != 'German' and self.dict[obj2_id][self.l1]['singular']['article'] != '':
					obj2 = self.dict[obj2_id][self.l1]['singular']['article'] + ' ' + obj2
				to_say = to_say.replace('[obj_2?]', obj2.encode('utf8') + '?')
				to_say = to_say.replace('[obj_2]', obj2.encode('utf8'))
			if json_params['type'].upper() == 'OBJECT_MOVE_CRITERIUM':
				to_say = to_say.replace('[rel]', relations[json_params['rel']][self.l1].encode('utf8'))
			self.log_to_memory("request_answer", {
				"request_count": self.count_req,
				"l2_exposures": self._extract_l2_targets(to_say)
			})
			if self.count_req > 0:
				to_say = "<name>, " + to_say
			self.count_req += 1
			self.outputrealizer.say(to_say)
			print "======> SENDING MESSAGAGE COMPLETED: REQUEST_ANSWER"
			self.sendMessage(self.sock, "call:tablet.interactionmanager.request_answer_completed")
		elif json_params["type"].upper() == 'SENSOR_TOUCH_CRITERIUM':			
			to_say = speech_content['SENSOR_TOUCH_CRITERIUM'][self.l1]
			if json_params['obj_1'] == 'righthand':
				to_say = to_say.replace('[obj_1]', '{' + 'right' + '} arm')	
			elif json_params['obj_1'] == 'lefthand':
				to_say = to_say.replace('[obj_1]', '{' + 'left' + '} arm')				
			self.log_to_memory("request_answer", {
				"request_count": self.count_req,
				"l2_exposures": self._extract_l2_targets(to_say)
			})
			if self.count_req > 0:
				to_say = "<name>, " + to_say
			self.count_req += 1
			self.outputrealizer.say(to_say)
                        print "======> SENDING MESSAGAGE COMPLETED: REQUEST_ANSWER"
			self.sendMessage(self.sock, "call:tablet.interactionmanager.request_answer_completed")
		else:
			pass

	def _move_on_tablet(self, obj_id, x, y, z, timeout, loop, use_IM = False):
		# look at tablet and perform behavior -> move
		self.outputrealizer.set_gaze('tablet')
		self.outputrealizer.start_behavior('move/tablet')
		# wait a second
		time.sleep(2)
		obj_toselect = {"ids": 
			[
				obj_id
			]				
		}		
		self.sendMessage(self.sock, "call:tablet.WebSocket.showTouch|%s" % (json.dumps(obj_toselect)))
		data = {
			'id': obj_id,
			'position': {
				'x': float(x),
				'y': float(y),
				'z': float(z)
			},
			'timeout': float(timeout),
			'loop': loop
		}
		if use_IM:
			self.sendMessage(self.sock, "call:tablet.interactionmanager.move_object|%s" % (json.dumps(data)))
		else:
			self.sendMessage(self.sock, "call:tablet.WebSocket.moveObject|%s" % (json.dumps(data)))
		time.sleep(1)
		self.sendMessage(self.sock, "call:tablet.WebSocket.hideTouch")

	def give_help(self, params):
		json_params = json.loads(params)
		speech_content = {
			'OBJECT_SELECT_CRITERIUM': {
				'English': 'Touch [obj_id] on the tablet',
				'Dutch': 'Ik zal het een keertje voordoen. Kijk maar.',
				'German': ''
			},
			'VOICE_ACTIVATION_CRITERIUM': {
				'English': 'Let\'s repeat it together. 3. 2. 1!',
				'Dutch': 'Laten we het samen zeggen. 3. 2. 1!',
				'German': '',
			},
			'OBJECT_MOVE_CRITERIUM': {
				'English': 'Let\'s put [obj_1] [rel] [obj_2]',
				'Dutch': 'Ik zal het een keertje voordoen, Kijk maar.',
				'German': ''
			},
			'OBJECT_MOVE_CRITERIUM_2D': {
				'English': 'Let\'s put [obj_1] [rel] [obj_2]',
				'Dutch': 'Ik zal het een keertje voordoen, Kijk maar.',
				'German': ''
			},			
			'OBJECT_COLLISION_CRITERIUM': {
				'English': 'Let\'s put [obj_1] [rel] [obj_2]',
				'Dutch': 'Ik zal het een keertje voordoen, Kijk maar.',
				'German': ''
			}			
		}
		print params		
		if json_params["type"] == "OBJECT_SELECT_CRITERIUM":
			# 1. look, I will show you
			self.log_to_memory("give_help", {
				"l2_exposures": self._extract_l2_targets(speech_content['OBJECT_SELECT_CRITERIUM'][self.l1])
			})			
			self.outputrealizer.say(speech_content['OBJECT_SELECT_CRITERIUM'][self.l1])
			# 2. look at tablet and perform behavior -> tap
			self.outputrealizer.set_gaze('tablet')
			self.outputrealizer.start_behavior('touch/tablet')
			time.sleep(2.5)	
			# 3. highlight object
			obj_toselect = {"ids": 
				[
					json_params["obj_1"]
				]				
			}
			self.sendMessage(self.sock, "call:tablet.WebSocket.showTouch|%s" % (json.dumps(obj_toselect)))
			# 4. wait a second
			time.sleep(1)
			# 5. remove highlight
			self.sendMessage(self.sock, "call:tablet.WebSocket.hideTouch")			
			time.sleep(0.5)
		elif json_params["type"] == "OBJECT_MOVE_CRITERIUM" or json_params["type"] == "OBJECT_COLLISION_CRITERIUM" or json_params["type"] == "OBJECT_MOVE_CRITERIUM_2D":
			current_task_output = self._get_output_for_task(self.latest_task)
			for cto in current_task_output:
				if cto['type'] == 'TEXT_OUTPUT':
					objective = cto['objective']
					break
			# Sanity check, should never happen though
			if objective == None:
				return
			# 1. look, I will show you
			self.log_to_memory("give_help", {
				"l2_exposures": self._extract_l2_targets(speech_content[json_params["type"]][self.l1])
			})				
			self.outputrealizer.say(speech_content[json_params["type"]][self.l1])
			# 2. highlight object and trigger the move
			self._move_on_tablet(json_params["obj_1"], objective['target_location']['x'], objective['target_location']['y'], objective['target_location']['z'], 1, 'false')
			if json_params["type"] == "OBJECT_COLLISION_CRITERIUM":
				data = {
					"obj_1": json_params["obj_1"],
					"obj_2": json_params["obj_2"]
				}
				if 'disappear' in objective:
					data['disappear'] = objective['disappear']
					if not objective['disappear']:
						data['target_location'] = objective['target_location']
				else:
					data['disappear'] = True
				self.sendMessage(self.sock, "call:tablet.WebSocket.showCollisionFeedback|%s" % (json.dumps(data)))
			time.sleep(4)
		elif json_params["type"] == "VOICE_ACTIVATION_CRITERIUM":
			self.outputrealizer.set_gaze('child')
			obj = self.dict[json_params['word']][self.l2]['singular']['text']
			# 1. Let's say it together. 3. 2. 1. {L2}
			self.log_to_memory("give_help", {
				"l2_exposures": self._extract_l2_targets(speech_content['VOICE_ACTIVATION_CRITERIUM'][self.l1] + ' {' + obj + '}')
			})				
			self.outputrealizer.say(speech_content['VOICE_ACTIVATION_CRITERIUM'][self.l1] + ' {' + obj + '}')
			time.sleep(2)
		elif json_params["type"] == "SENSOR_TOUCH_CRITERIUM":
			self.log_to_memory("give_help", {
				"l2_exposures": []
			})			
			self.outputrealizer.toggle_touch_sensors(False)
			self.outputrealizer.toggle_breathing(True)
		self._check_and_run_tablet_output()
		print "======> SENDING MESSAGAGE COMPLETED: HELP"
		self.sendMessage(self.sock, "call:tablet.interactionmanager.help_completed")

	def grab_attention(self):
		# @TODO: implement me
		pass

	def interrupt_output(self, give_instruction = False):
		self.outputrealizer.interrupt_output(give_instruction == "true")

	def set_child_name(self, name):
		logging.debug("Setting child name: " + name)
		self.outputrealizer.set_variable('name', name)

	def _convert_lang_string(self, lang):
		if lang == 'Dut':
			return 'Dutch'
		elif lang == 'Eng':
			return 'English'
		elif lang == 'Ger':
			return 'German'
		elif lang == 'Tur':
			return 'Turkish'

		return None

	def say(self, text):
		if not self.outputrealizer.robot_volume_enabled:
			self.outputrealizer.toggle_robot_volume(True)
			self.outputrealizer.say(text)
			self.outputrealizer.toggle_robot_volume(False)
		else:
			self.outputrealizer.say(text)

	def set_lang(self, params):
		# Ignoring the setting for now, forcing Dutch -> English ;)
		print params
		self.l1 = 'Dutch'
		self.l2 = 'English'
		self.outputrealizer.set_languages(self.l1, self.l2)
		self.tabletmanager.set_languages(self.l1, self.l2)
		self.tabletconditionmanager.set_languages(self.l1, self.l2)

	def sensor_touched_callback(self, arm_id):
		print "=== sensor touched " + arm_id
		self.sendMessage(self.sock, 'call:tablet.interactionmanager.sensor_touched|{"id":"' + arm_id + '"}')

	def move_object_callback(self, param):
		params = param.lower().split(',')
		print "==== MOVE OBJECT ===="
		print params
		self._move_on_tablet(params[0].strip(), params[1].strip(), params[2].strip(), params[3].strip(), params[4].strip(), params[5].strip(), True)

	def tablet_screen_callback(self, message):
		logging.debug("Switching tablet screen " + message)
		if message.lower() == 'on':
			self.sendMessage(self.sock, "call:tablet.WebSocket.showTablet")
		elif message.lower() == 'off':
			self.sendMessage(self.sock, "call:tablet.WebSocket.hideTablet")		

	def accept_answer_callback(self, dummy_value):
		self.sendMessage(self.sock, 'call:tablet.interactionmanager.accept_answer')

	def _spawn_thread(self, method, params):
		try:
			getattr(self, method)(params)
		finally:
			self._thread_complete_callback(threading.currentThread())

	def _thread_complete_callback(self, thread_ref):
		self.worker_threads.remove(thread_ref)

	def exit_interaction(self,  params):
		logging.debug("Exit message received, quitting OutputManager..")
		self.running = False

	def log_child_information(self, params):
		print params
		json_params = json.loads(params)
		if json_params['condition'] == 'Robot + Iconic':
			self.is_gesture_condition = True
			self.is_tablet_condition = False
		elif json_params['condition'] == 'Robot + Non-Iconic':
			self.is_gesture_condition = False
			self.is_tablet_condition = False
		elif json_params['condition'] == 'Tablet Only':
			self.is_gesture_condition = False
			self.is_tablet_condition = True
			self.delay_timer_activated = False
		if self.is_tablet_condition:
			self.wait_tabletcondition = True
			if not self.tabletconditionmanager.start_output_rerouting():
				# Something went wrong..
				print "==== PROBLEM WITH STARTING THE TABLET CONDITION! ==="
				print "Please restart the experiment."
			else:
				self.wait_tabletcondition = False
		self.outputrealizer.update_for_condition()


	# In case we are running as a service on the NAO, qiapp will already be initialized.
	# Ideally we don't want OutputManager to know NAO-specific things, but in case of running
	# as a service this seems to be the way to go for now?
	def __init__(self, qiapp = None, nao_ip = None, server_ip = None):
		self.running = True
		self.loadedSession = None
		self.l1 = 'Dutch'
		self.l2 = 'English'
		self.prev_l2 = {}
		self.nao_ip = nao_ip
		self.delay_timer_activated = False
		self.is_test = False
		self.wait_tabletcondition = False
		self.outputrealizer = OutputRealizer(self, qiapp, nao_ip)
		self.tabletconditionmanager = TabletConditionManager(self.nao_ip, self.l1, self.l2)
		self.tabletmanager = TabletManager(self)
		# Some defaults, will be replaced by control panel upon starting the experiment
		self.is_gesture_condition = True
		self.is_tablet_condition = False
		# Load the dictionary for looking up target and support words
		# For now, we use one big dictionary for all content, maybe this will be split up later.
		with open(os.path.join(os.path.dirname(__file__), '../../../datamodel/sessions/outputmanager/dictionary.json')) as infile:
			self.dict = json.load(infile)
		self.worker_threads = list()
		# @TODO: this should include the message from the control panel later on
		self.set_lang('Dut-Eng')
		self.feedbackmanager = FeedbackManager(self)
                # Connect to the ConnectionManager
		ip = "127.0.0.1"
		if server_ip != None:
			ip = server_ip
		port = 1111
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
		server_address = (ip, 1111)
		self.sock.connect(server_address) 
		self.sock.settimeout(1)
		a_messages = Queue()
		self.t = threading.Thread(target=self.readMessages, args=(self.sock, a_messages))
		self.t.start()
                # Register this module with the ConnectionManager
		self.sendMessage(self.sock,"register:outputmanager")
		# Repeatedly look for new messages and handle them
		try:
			while self.running:
				try:
					str_message = a_messages.get_nowait()
					if str_message != "":
						logging.debug("Message received: " + str_message)
						fields = str_message.split("|")
						sender, method, params = fields[:3]
						wt = threading.Thread(target=self._spawn_thread, args=(method, params))
						self.worker_threads.append(wt)
						wt.start()
					a_messages.task_done()
				except Empty:
					pass
				time.sleep(0.1)
			self.cleanup()
		except KeyboardInterrupt:
			self.cleanup()

	def cleanup(self):
		global runningReading
		self.sendMessage(self.sock, "exit")
		self.outputrealizer.clean_up()
		# Clean up all worker threads that may be left running
		for wt in self.worker_threads:
			print "Worker thread found, cleaning:"
			print wt
			wt.join()
		runningReading = False
		self.t.join()
		self.sock.close()

	def sendMessage(self, socket, strMessage):
		#send the message in parameter
		logging.debug("Sending message: " + strMessage)
		socket.sendall(strMessage + "#")
		time.sleep(0.1)

	def readMessages(self, _socket, a_messages):
	"""
            This function receives all messages send over the socket connection.

            :param _socket: The TCP Socket.
            :param a_messages: A list where all messages have to be stored.
        """
		tmp_messages = []
		while runningReading:
			try:
				str_receive = _socket.recv(1024)
				if "#" in str_receive:
					str_receive = str_receive.split("#")
					if len(str_receive) > 1:
						tmp_messages += str_receive[0]
						a_messages.put("".join(tmp_messages)) if len(tmp_messages) > 1 else a_messages.put(tmp_messages[0])
						for r in str_receive[1:-1]:
							a_messages.put(r)
					tmp_messages = [str_receive[-1]]
				else:
					tmp_messages.append(str_receive)
			except socket.error, e:
				pass

if __name__ == "__main__":
	# Start the logging
	# if log dir doesn't exist ...
	if not os.path.exists('c:/l2tor/logs'):
		# ... create it
		os.makedirs('c:/l2tor/logs')
	logFile = 'c:/l2tor/logs/om_' + time.strftime('%Y%m%d%H%M%S') + '.log'
	logging.basicConfig(filename=logFile, 
						level=logging.DEBUG, 
						format='%(levelname)s %(asctime)-15s %(threadName)s %(message)s (%(module)s.%(lineno)d)',
						datefmt='%H.%M.%S',
						filemode='w')	
	logFormatter = lf.LogFormatter(filename=logFile,level=lf.INFO)
	logFormatter.start()	
	# Parse command-line options
	parser = OptionParser()
	parser.add_option("-s", "--server-ip", dest="server_ip", help="IP address of the ConnectionManager server")
	parser.add_option("-r", "--robot-ip", dest="robot_ip", help="IP address of the robot", default=None)
	(options, args) = parser.parse_args()
	if options.robot_ip == None:
		# Try to discover the robot's IP based on its name on the network
		try:
			logging.info("No robot IP provided -- trying to find it automatically..")
			ip = socket.gethostbyname('Zora.local')
			OutputManager(None, ip, options.server_ip)
		except Exception as e:
			logging.info("Could not automatically detect the robot's IP -- exiting!")
	else:
		OutputManager(None, options.robot_ip, options.server_ip)
