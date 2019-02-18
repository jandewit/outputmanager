import paramiko
import os
import subprocess
import netifaces as ni
import time
import logging

if os.name == "nt":
	import _winreg as wr

class TabletConditionManager:
	def set_languages(self, l1, l2):
		self.l1 = l1
		self.l2 = l2

	# Borrowed from the ConnectionManager ;)
	def get_network_guid(self, iface_guids, networkType):
		reg = wr.ConnectRegistry(None, wr.HKEY_LOCAL_MACHINE)
		reg_key = wr.OpenKey(reg, r'SYSTEM\ControlSet001\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}')
		for i in range(len(iface_guids)):
			try:
				reg_subkey = wr.OpenKey(reg_key, iface_guids[i] + r'\Connection')
				name = wr.QueryValueEx(reg_subkey, 'Name')[0]
				if networkType == "wifi":
					if "Wi-Fi" in name or "WiFi" in name or "sans fil" in name or "Wireless Network Connection" in name:
						# The problem here is that my laptop has an unused "Wireless Network Connection 2"
						# which is now returned and does not have an IP assigned. So we need to see if a connection is actually present
						addr = ni.ifaddresses(iface_guids[i])
						if 2 in addr:
							return iface_guids[i]
				else:
					if "Ethernet" in name or "Local Area Connection" in name:
						addr = ni.ifaddresses(iface_guids[i])
						if 2 in addr:
							return iface_guids[i]
			except OSError as e:
				pass
		return None

	def start_output_rerouting(self):	
		# Link NAO to the speakers
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		# @TODO: remove password from the sourcecode and get the ip from the main outputmanager
		client.connect(self.nao_ip, username='nao', password=self.password)
		stdin,stdout,stdderr = client.exec_command('pacmd load-module module-tunnel-sink sink_name=nao server=' + self.ip)
		stdin,stdout,stdderr = client.exec_command('pacmd list-sinks')
		response = stdout.read()
		sink_index = -1
		lines = response.splitlines()
		for l in range(0,len(lines)):
			if lines[l].find('<nao>') != -1:
				sink_index = lines[l-1].split(':')[1].strip()
				break
		if sink_index == -1:
			return False
		stdin,stdout,stdderr = client.exec_command('pacmd set-default-sink ' + sink_index)
		stdin,stdout,stdderr = client.exec_command('qicli call ALAudioDevice._setDefaultOutput ' + sink_index)
		print stdout.read()
		# I'm not even kidding you, but the sound is stuttering until you do a language switch..
		# By switching twice, we force an actual change (no matter what its initial language setting is), while guaranteeing
		# that we end up with the L1 to start the experiment.
		stdin,stdout,stdderr = client.exec_command('qicli call ALTextToSpeech.setLanguage "' + self.l2 + '"')
		print stdout.read()
		stdin,stdout,stdderr = client.exec_command('qicli call ALTextToSpeech.setLanguage "' + self.l1 + '"')
		print stdout.read()
		client.close()
		self.is_rerouting = True
		return True

	def remove_pid_file(self):
		try:
			username = os.environ.get("USERNAME")
			computername = os.environ.get("COMPUTERNAME")
			os.remove('C:/Users/' + username + '/.pulse/' + computername + '-runtime/pid')
		except:
			print "Error removing pid file"
			pass

	def stop_output_rerouting(self):
		# Stop the daemon
		self.pulse_proc.kill()
		# Delete the pid file just in case -- might not be needed thanks to different configuration setting.
		#self.remove_pid_file()
		# Remove the link from NAO
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		# @TODO: remove password from the sourcecode and get the ip from the main outputmanager
		client.connect(self.nao_ip, username='nao', password=self.password)
		stdin,stdout,stdderr = client.exec_command('pacmd set-default-sink 0')
		stdin,stdout,stdderr = client.exec_command('qicli call ALAudioDevice._setDefaultOutput 0')
		client.close()
		self.is_rerouting = False

	def __init__(self, nao_ip = None, l1 = "Dutch", l2 = "English"):
		self.ip = "127.0.0.1"
		self.is_rerouting = False
		self.nao_ip = nao_ip
		self.l1 = l1
		self.l2 = l2
		self.password = ""
		# Retrieve the top secret password
		script_dir = os.path.realpath(__file__).split('tabletconditionmanager.py')[0]
		if(os.path.exists(script_dir + '/pass.txt')):
			with open(script_dir + '/pass.txt', 'r') as f:
				self.password  = f.readline()
		else:
			logging.debug("Password file not found!")
		if self.password != "":
			try:
				if os.name == "nt":				
					# We force ethernet for now
					guid = self.get_network_guid(ni.interfaces(), "ethernet")
					self.ip      = ni.ifaddresses(guid)[2][0]['addr']
				else:
					if args.networkType == "ethernet":
						self.ip      = ni.ifaddresses('eth0')[2][0]['addr']
					else:
						self.ip      = ni.ifaddresses('wlan0')[2][0]['addr']
			except Exception, e:
				pass
			# Delete the pid file just in case -- might not be needed thanks to different configuration setting.
			#self.remove_pid_file()
			# Starting the daemon
			self.pulse_proc = subprocess.Popen([script_dir + '/PulseAudio/bin/PulseAudio.exe', '-F', script_dir + '/PulseAudio/bin/config.pa'])

	def __del__(self):
		if self.is_rerouting:
			self.stop_output_rerouting()

if __name__ == "__main__":
	tcm = TabletConditionManager("192.168.1.99", "Dutch", "English")
	tcm.start_output_rerouting()

	try:
		while True:
			time.sleep(0.1)

	except KeyboardInterrupt:
		pass
