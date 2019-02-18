"""
Output Manager service
"""

__version__ = "0.0.1"

__copyright__ = "Copyright 2016, L2TOR project"
__author__ = 'L2TOR team Tilburg'
__email__ = 'all@l2tor.eu'

import qi
import stk.runner
from outputmanager import OutputManager

class ALOutputManagerService(object):
    "NAOqi service example (set/get on a simple value)."
    APP_ID = "com.aldebaran.ALMyService"
    def __init__(self, qiapp):
        # generic activity boilerplate
        self.qiapp = qiapp
        OutputManager(qiapp)

    @qi.bind(returnType=qi.Void, paramsType=[])
    def stop(self):
        "Stop the service."
        self.logger.info("ALOutputManagerService stopped by user request.")

    @qi.nobind
    def on_stop(self):
        "Cleanup (add yours if needed)"
        self.logger.info("ALOutputManagerService finished.")

####################
# Setup and Run
####################

if __name__ == "__main__":
    stk.runner.run_service(ALOutputManagerService)

