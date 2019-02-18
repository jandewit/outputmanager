# Output Manager #
The OutputManager takes inputs (metadata) from the InteractionManager and produces robot outputs (speech synthesis and non-verbal behaviour).

# License #
This code was developed as part of the L2TOR project, which has received funding from the European Union’s Horizon 2020 research and innovation programme under the Grant Agreement No. 688014.

If you use this system in any way, please include a reference to the following paper:

@inproceedings{vogt2019second,
  title={Second Language Tutoring using Social Robots: A Large-Scale Study},
  author={Vogt, Paul and van den Berghe, Rianne and de Haas, Mirjam and Hoffmann, Laura and Kanero, Junko and Mamus, Ezgi and Montanier, Jean-Marc and Oran\c{c}, Cansu and Oudgenoeg-Paz, Ora and Garc\'{i}a, Daniel Hern\'{a}ndez and Papadopoulos, Fotios and Schodde, Thorsten and Verhagen, Josje and Wallbridge, Christopher D. and Willemsen, Bram and de Wit, Jan and Belpaeme, Tony and G\"{o}ksun, Tilbe and Kopp, Stefan and Krahmer, Emiel and K\"{u}ntay, Aylin C. and Leseman, Paul and Pandey, Amit K.},
  booktitle={Proceedings of the 2019 ACM/IEEE International Conference on Human-Robot Interaction},
  year={2019},
  organization={ACM/IEEE}
}

### Installation: ###
1. The following library is needed for audio playback:
```
pip install pyaudio (might need PortAudio on some devices, did not on my Windows machine)
```

2. Install the gaze.pml file to your robot via Choregraphe to get the non-verbal behaviours to work.
3. For logging we are using the log_formatter that can be installed from http://protolab.aldebaran.com:9000/protolab/log_formatter

4. For the tablet condition, we need a framework called Paramiko:
```
pip install paramiko
```

5. IMPORTANT: you need to place a file called pass.txt in /OutputManager/app/scripts/submodules/ that contains the password to NAO via SSH. I did not add this for security reasons (and because it may differ between NAOs)

### Running: ###

```
$ python app/scripts/outputmanager.py
```

Parameters:
1. -s [connectionmanager-ip]
2. -r [robot-ip]

### Testing: ###

For testing, we created a mock_interactionmanager that sends some messages to the OutputManager in order to test its workings, without having to rely on the actual InteractionManager.

The unit tests in testrun.py currently do not work anymore, because the service itself only starts the connection with ConnectionManager.