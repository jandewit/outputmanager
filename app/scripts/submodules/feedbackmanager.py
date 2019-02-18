import csv
import random
import os.path
"""to whomever is trying to make sense of this mess: godspeed, you brave individual"""
class FeedbackManager:

	def get_feedback(self, json_params):
		self.json_params = json_params
		self.valid = self.json_params['valid'] 
		self.task_type = self.json_params['type']
		self.pos_prev_fb = ''
		self.neg_prev_fb = ''
		self.voice_act_prev_fb = ''
		# should be loaded from elsewhere, with picks for each language, rather than hardcoded
		self.pos_fb_picks = ['Wauw wat knap!', 'Goed gedaan!', 'Heel goed!',
                                     'Goedzo!', 'Wat knap!', 'Heel knap!', 'Helemaal goed!',
                                     'Goed bezig!', 'Knap hoor!', 'Super!', 'Wauw wat goed!']		
                self.neg_fb_picks = ['Goed geprobeerd, maar ', 'Bijna, maar ', 'Jammer, maar ',
                                     'Helaas, maar ', 'Bijna, maar dat is niet helemaal goed',
                                     'Jammer, dat klopt niet helemaal.', 'Dat is niet helemaal goed.',
                                     'Jammer, dat is niet helemaal goed.', 'Helaas, dat klopt niet helemaal.',
                                     'Helaas, dat is niet helemaal goed.'] # same as ^
                self.voice_act_fb_picks = ['Dat heb je knap gezegd!', 'Knap gezegd!', 'Wat knap!',
                                           'Goed bezig!', 'Knap hoor!', 'Super!', 'Wauw knap gezegd!']                
                self.pos_nv_tag = "<face(happy)>"
                #this doesn't belong here, but let's ignore that for now
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
			}			
		}
                #same as ^
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
		if self.task_type == "OBJECT_SELECT_CRITERIUM":
			self.current_task_output = self.outputmanager._get_output_for_task(self.outputmanager.latest_task)
			for cto in self.current_task_output:
				if cto['type'] == 'TEXT_OUTPUT':
					self.objective = cto['objective']
					break			
			self.target = self.outputmanager._obj_json_to_string(self.objective)
			self.article = self.target.split(' ')[0]
			self.target_word = " ".join(self.target.split(' ')[1:]) #will this work for L2?
			if self.valid == 0: 
				if self.L1 == "Dutch":
                                        self.target_obj = self.target                                        
                                        # Add a relation if it is there
                                        if 'rel' in self.objective:
                                                # The relation is with another object so we should also add that :)
                                                if self.objective['rel']['type'] == 'more' or self.objective['rel']['type'] == 'most' or self.objective['rel']['type'] not in self.relations:
                                                        self.obj2 = self.outputmanager._obj_json_to_string(self.objective['rel']['target'], False)
                                                        self.target_obj += ' ' + self.relations['with'][self.L1]
                                                else:
                                                        self.obj2 = self.outputmanager._obj_json_to_string(self.objective['rel']['target'])
                                                self.to_find = self.objective['rel']['type']				
                                                if self.objective['rel']['type'] in self.relations:
                                                        self.to_find = self.relations[self.objective['rel']['type']][self.L2]
                                                if self.outputmanager._find_if_l2(self.to_find):
                                                        # Sometimes this can be a number, so we should check if the relation is known
                                                        if self.objective['rel']['type'] in self.relations:
                                                                self.target_obj += ' {' + self.relations[self.objective['rel']['type']][self.L2]
                                                        else:
                                                                self.target_obj += ' {' + self.dict[self.objective['rel']['type']][self.L2]['singular']['text']
                                                        if self.obj2.startswith('{'):
                                                                self.target_obj += ' ' + self.obj2[1:]
                                                        else:
                                                                self.target_obj += '} ' + self.obj2
                                                else:
                                                        # Sometimes this can be a number, so we should check if the relation is known
                                                        if self.objective['rel']['type'] in self.relations:
                                                                self.target_obj += ' ' + self.relations[self.objective['rel']['type']][self.L1]					
                                                        else:
                                                                self.target_obj += ' ' + self.dict[self.objective['rel']['type']][self.L1]['singular']['text']
                                                        self.target_obj += ' ' + self.obj2
                                                self.neg_current_fb = ''
                                                while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                        self.neg_current_fb = random.choice(self.neg_fb_picks)
                                                self.neg_prev_fb = self.neg_current_fb
                                                if self.count_fb > 0:
                                                        self.outputmanager.log_to_memory("feedback", {
                                                                "feedback_count": self.count_fb,
                                                		"is_positive": False,
                                                		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                                		"l2_exposures": self.outputmanager._extract_l2_targets(self.target_obj)
                                                	})
                                                        return self.neg_current_fb + "Je moet {0} aanraken.".format(self.target_obj)
                                                else:
                                                	self.outputmanager.log_to_memory("feedback", {
                                                		"feedback_count": self.count_fb,
                                                		"is_positive": False,
                                                		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                                		"l2_exposures": self.outputmanager._extract_l2_targets(self.target_obj)
                                                	})
                                                        self.count_fb += 1
                                                        return self.neg_current_fb + "Je moet {0} aanraken. Probeer het nog maar een keer.".format(self.target_obj)
                                        else:
                                                self.neg_current_fb = ''
                                                while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                        self.neg_current_fb = random.choice(self.neg_fb_picks)
                                                self.neg_prev_fb = self.neg_current_fb
                                                if self.count_fb > 0:
                                                	self.outputmanager.log_to_memory("feedback", {
                                                		"feedback_count": self.count_fb,
                                                		"is_positive": False,
                                                		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                                		"l2_exposures": self.outputmanager._extract_l2_targets((self.article + " " + self.target_word))
                                                	})
                                                        return self.neg_current_fb + "Je moet {0} {1} aanraken.".format(self.article, self.target_word)
                                                else:
                                                	self.outputmanager.log_to_memory("feedback", {
                                                		"feedback_count": self.count_fb,
                                                		"is_positive": False,
                                                		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                                		"l2_exposures": self.outputmanager._extract_l2_targets((self.article + " " + self.target_word))
                                                	})
                                                        self.count_fb += 1
                                                        return self.neg_current_fb + "Je moet {0} {1} aanraken. Probeer het nog maar een keer.".format(self.article, self.target_word)
				elif self.L1 == "English":
					pass
				elif self.L1 == "German":
					pass
			elif self.valid == 1:
                                # random pick from a list of feedback utterances, might be overkill here
                                self.pos_current_fb = ''
                                while self.pos_current_fb == '' or self.pos_current_fb == self.pos_prev_fb:
                                        self.pos_current_fb = random.choice(self.pos_fb_picks)
                                self.pos_prev_fb = self.pos_current_fb
                                self.outputmanager.log_to_memory("feedback", {
                                        "feedback_count": self.count_fb,
                                        "is_positive": True,
                                        "variation": self.pos_fb_picks.index(self.pos_current_fb),
                                        "l2_exposures": []
                                })                                
				return self.pos_nv_tag + self.pos_current_fb
		elif self.task_type == "OBJECT_MOVE_CRITERIUM":
			self.current_task_output = self.outputmanager._get_output_for_task(self.outputmanager.latest_task)
			for cto in self.current_task_output:
				if cto['type'] == 'TEXT_OUTPUT':
					self.objective = cto['objective']
					break
			self.target = self.outputmanager._obj_json_to_string(self.objective)
			self.article = self.target.split(' ')[0]
			self.target_word = " ".join(self.target.split(' ')[1:])
                        moved_object = json_params['ADD_INFO']['moved_object']
                        target_object = json_params['ADD_INFO']['target_object']
                        goal_object = json_params['ADD_INFO']['goal_object']
                        target_sprel = json_params['ADD_INFO']['target_sprel']
                        if target_object.rfind('_') != -1 and self.outputmanager._is_numeric(target_object[target_object.rfind('_')+1]):
				target_object = target_object[:target_object.rfind('_')]
			if goal_object.rfind('_') != -1 and self.outputmanager._is_numeric(goal_object[goal_object.rfind('_')+1]):
				goal_object = goal_object[:goal_object.rfind('_')]
                        obj1_id = target_object 
			if obj1_id.rfind('_') != -1 and self._is_numeric(obj1_id[obj1_id.rfind('_')+1]):
				obj1_id = obj1_id[:obj1_id.rfind('_')]	
			obj2_id = goal_object
			if obj2_id.rfind('_') != -1 and self._is_numeric(obj2_id[obj2_id.rfind('_')+1]):
				obj2_id = obj2_id[:obj2_id.rfind('_')]	
			to_say = speech_content[json_params['type'].upper()][self.L1]
			# For now, we assume a move action is always moving 1 item next to 1 other item (all singular)
                        self.l1 = self.L1
                        self.l2 = self.L2  
			if self.outputmanager._find_if_l2(self.dict[obj1_id][self.l2]['singular']['text']):
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
			if self.outputmanager._find_if_l2(self.dict[obj2_id][self.l2]['singular']['text']):
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
				to_say = to_say.replace('[rel]', relations[json_params['ADD_INFO']['target_sprel']][self.l1].encode('utf8'))
			"""
				Parse relationship from objective, if relationship exists
				Code copy-pasted from request_answer in OutputManager
			"""
                        self.target_obj = self.target			
			# Add a relation if it is there
			if 'rel' in self.objective:
				# The relation is with another object so we should also add that :)
				if self.objective['rel']['type'] == 'more' or self.objective['rel']['type'] == 'most' or self.objective['rel']['type'] not in self.relations:
					self.obj2 = self.outputmanager._obj_json_to_string(self.objective['rel']['target'], False)
					self.target_obj += ' ' + self.relations['with'][self.L1]
				else:
					self.obj2 = self.outputmanager._obj_json_to_string(self.objective['rel']['target'])
				self.to_find = self.objective['rel']['type']				
				if self.objective['rel']['type'] in self.relations:
					self.to_find = self.relations[self.objective['rel']['type']][self.L2]
				if self.outputmanager._find_if_l2(self.to_find):
					# Sometimes this can be a number, so we should check if the relation is known
					if self.objective['rel']['type'] in self.relations:
						self.target_obj += ' {' + self.relations[self.objective['rel']['type']][self.L2]
					else:
						self.target_obj += ' {' + self.dict[self.objective['rel']['type']][self.L2]['singular']['text']
					if self.obj2.startswith('{'):
						self.target_obj += ' ' + self.obj2[1:]
					else:
						self.target_obj += '} ' + self.obj2
				else:
					# Sometimes this can be a number, so we should check if the relation is known
					if self.objective['rel']['type'] in self.relations:
						self.target_obj += ' ' + self.relations[self.objective['rel']['type']][self.L1]				
					else:
						self.target_obj += ' ' + self.dict[self.objective['rel']['type']][self.L1]['singular']['text']
					self.target_obj += ' ' + self.obj2
			if self.valid == 0: 
				if self.L1 == "Dutch":
                                        self.neg_current_fb = ''
                                        while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                self.neg_current_fb = random.choice(self.neg_fb_picks)
                                        self.neg_prev_fb = self.neg_current_fb
                                        if self.count_fb > 0:
                                                try:
                                                	self.outputmanager.log_to_memory("feedback", {
                                                		"feedback_count": self.count_fb,
                                                		"is_positive": False,
                                                		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                                		"l2_exposures": self.outputmanager._extract_l2_targets(self.target_obj)
                                                	})                                                        
                                                        return self.neg_current_fb + "Je moet {0} zetten.".format(self.target_obj)
                                                        # should not always say "probeer het nog maar een keer"; when robot gives help, no option to try again
                                                except:
                                                        return "object move fout. template did not work"
                                        else:
                                                try:
                                                	self.outputmanager.log_to_memory("feedback", {
                                                		"feedback_count": self.count_fb,
                                                		"is_positive": False,
                                                		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                                		"l2_exposures": self.outputmanager._extract_l2_targets(self.target_obj)
                                                	})
                                                        self.count_fb += 1
                                                        return self.neg_current_fb + "Je moet {0} zetten. Probeer het nog maar een keer.".format(self.target_obj)
                                                        # should not always say "probeer het nog maar een keer"; when robot gives help, no option to try again
                                                except:
                                                        self.count_fb += 1
                                                        return "object move broken. template did not work"
				elif self.L1 == "English":
					pass
				elif self.L1 == "German":
					pass
			elif self.valid == 1:
                                self.pos_current_fb = ''
                                while self.pos_current_fb == '' or self.pos_current_fb == self.pos_prev_fb:
                                        self.pos_current_fb = random.choice(self.pos_fb_picks)
                                self.pos_prev_fb = self.pos_current_fb
                              	self.outputmanager.log_to_memory("feedback", {
                              		"feedback_count": self.count_fb,
                               		"is_positive": True,
                               		"variation": self.pos_fb_picks.index(self.pos_current_fb),
                               		"l2_exposures": []
                               	})                                
				return self.pos_nv_tag + self.pos_current_fb
		elif self.task_type == "VOICE_ACTIVATION_CRITERIUM":
			self.current_task_output = self.outputmanager._get_output_for_task(self.outputmanager.latest_task)
			for cto in self.current_task_output:
				if cto['type'] == 'TEXT_OUTPUT':
					self.objective = cto['objective']
					break
			self.target = self.outputmanager._obj_json_to_string(self.objective)
			if 'the ' in self.target:
                                self.target = self.target.replace('the ', '') #this is very bad, but then again most of this is
			if self.valid == 0: #this should not happen anymore: button disabled in control panel
				if self.L1 == "Dutch":
                                        self.neg_current_fb = ''
                                        while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                self.neg_current_fb = random.choice(self.neg_fb_picks)
                                        self.neg_prev_fb = self.neg_current_fb
                                        if self.count_fb > 0:
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": self.outputmanager._extract_l2_targets(self.target)
                                               	})                                                
                                                return self.neg_current_fb + "Je moet {0} zeggen.".format(self.target)
                                        else:
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": self.outputmanager._extract_l2_targets(self.target)
                                               	})                                                
                                                self.count_fb += 1
                                                return self.neg_current_fb + "Je moet {0} zeggen. Probeer het nog maar een keer.".format(self.target)
				elif self.L1 == "English":
					pass
				elif self.L1 == "German":
					pass
			elif self.valid == 1: #although validated as 1, feedback should not be positive
                                # random pick from a list of feedback utterances
                                self.voice_act_current_fb = ''
                                while self.voice_act_current_fb == '' or self.voice_act_current_fb == self.voice_act_prev_fb:
                                        self.voice_act_current_fb = random.choice(self.voice_act_fb_picks)
                                self.voice_act_prev_fb = self.voice_act_current_fb
                                self.outputmanager.log_to_memory("feedback", {
                                        "feedback_count": self.count_fb,
                                        "is_positive": True,
                                        "variation": self.voice_act_fb_picks.index(self.voice_act_current_fb),
                                        "l2_exposures": []
                                })                                
				return self.voice_act_current_fb
		elif self.task_type == "OBJECT_MOVE_CRITERIUM_2D": 
			if self.valid == 0: 
				if self.L1 == "Dutch":
                                        self.neg_current_fb = ''
                                        while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                self.neg_current_fb = random.choice(self.neg_fb_picks)
                                        self.neg_prev_fb = self.neg_current_fb
                                        if self.count_fb > 0:
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": []
                                               	})                                                
                                                return self.neg_current_fb
                                        else:
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": []
                                               	})                                                
                                                self.count_fb += 1
                                                return self.neg_current_fb + "Probeer het nog maar een keer."
				elif self.L1 == "English":
					pass
				elif self.L1 == "German":
					pass
			elif self.valid == 1:
                                self.pos_current_fb = ''
                                while self.pos_current_fb == '' or self.pos_current_fb == self.pos_prev_fb:
                                        self.pos_current_fb = random.choice(self.pos_fb_picks)
                                self.pos_prev_fb = self.pos_current_fb
                                self.outputmanager.log_to_memory("feedback", {
                                        "feedback_count": self.count_fb,
                                        "is_positive": True,
                                        "variation": self.pos_fb_picks.index(self.pos_current_fb),
                                        "l2_exposures": []
                                })                                 
				return self.pos_nv_tag + self.pos_current_fb
		elif self.task_type == "OBJECT_COLLISION_CRITERIUM": #apparently we do not give negative feedback for this criterium
			if self.valid == 0: 
				if self.L1 == "Dutch":
                                        self.neg_current_fb = ''
                                        while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                self.neg_current_fb = random.choice(self.neg_fb_picks)
                                        self.neg_prev_fb = self.neg_current_fb
                                        if self.count_fb > 0:
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": [] 
                                               	})                                                 
                                                return self.neg_current_fb 
                                        else:
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": [] 
                                               	})                                                 
                                                self.count_fb += 1
                                                return self.neg_current_fb + "Probeer het nog maar een keer." 
				elif self.L1 == "English":
					pass
				elif self.L1 == "German":
					pass
			elif self.valid == 1:
                                self.pos_current_fb = ''
                                while self.pos_current_fb == '' or self.pos_current_fb == self.pos_prev_fb:
                                        self.pos_current_fb = random.choice(self.pos_fb_picks)
                                self.pos_prev_fb = self.pos_current_fb
                                self.outputmanager.log_to_memory("feedback", {
                                        "feedback_count": self.count_fb,
                                        "is_positive": True,
                                        "variation": self.pos_fb_picks.index(self.pos_current_fb),
                                        "l2_exposures": []
                                })                                 
				return self.pos_nv_tag + self.pos_current_fb
		elif self.task_type == "SENSOR_TOUCH_CRITERIUM":
			if self.valid == 0:
				if self.L1 == "Dutch":
                                        self.neg_current_fb = ''
                                        while self.neg_current_fb == '' or self.neg_current_fb == self.neg_prev_fb:
                                                self.neg_current_fb = random.choice(self.neg_fb_picks)
                                        self.neg_prev_fb = self.neg_current_fb
                                        if self.count_fb > 0:
                                                if json_params['ADD_INFO']['target_sensor'] == 'righthand':
                                                        self.target = '{right}'
                                                elif json_params['ADD_INFO']['target_sensor'] == 'lefthand':
                                                        self.target = '{left}'
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": self.outputmanager._extract_l2_targets(self.target)
                                               	})                                                         
                                                return self.neg_current_fb + "Je moet mijn {0} arm aanraken.".format(self.target)
                                        else:
                                                if json_params['ADD_INFO']['target_sensor'] == 'righthand':
                                                        self.target = '{right}'
                                                elif json_params['ADD_INFO']['target_sensor'] == 'lefthand':
                                                        self.target = '{left}'
                                              	self.outputmanager.log_to_memory("feedback", {
                                              		"feedback_count": self.count_fb,
                                               		"is_positive": False,
                                               		"variation": self.neg_fb_picks.index(self.neg_current_fb),
                                               		"l2_exposures": self.outputmanager._extract_l2_targets(self.target)
                                               	})                                                        
                                                self.count_fb += 1
                                                return self.neg_current_fb + "Je moet mijn {0} arm aanraken. Probeer het nog maar een keer.".format(self.target)
			elif self.valid == 1:
                                self.pos_current_fb = ''
                                while self.pos_current_fb == '' or self.pos_current_fb == self.pos_prev_fb:
                                        self.pos_current_fb = random.choice(self.pos_fb_picks)
                                self.pos_prev_fb = self.pos_current_fb
                                self.outputmanager.log_to_memory("feedback", {
                                        "feedback_count": self.count_fb,
                                        "is_positive": True,
                                        "variation": self.pos_fb_picks.index(self.pos_current_fb),
                                        "l2_exposures": []
                                })                                
				return self.pos_nv_tag + self.pos_current_fb
		pass

	def __init__(self, outputmanager):		
		self.outputmanager = outputmanager
		self.dict = self.outputmanager.dict
		self.L1 = self.outputmanager.l1
		self.L2 = self.outputmanager.l2
		self.count_fb = 0
		self.relations = {
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
		pass

	def __del__(self):
		pass
