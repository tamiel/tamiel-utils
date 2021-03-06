from plivo.utils.logger import StdoutLogger, FileLogger, SysLogger
import os
from gevent.wsgi import WSGIServer
from flask import Flask
from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from api import RestApi
import urls



class RestServer(InboundEventSocket, RestApi):
    name = "RestServer"

    def __init__(self, configfile):
        os.environ['PLIVO_REST_CONFIG'] = configfile
        # create flask app
        self.app = Flask(self.name)
        # load config into flask app
        self.app.config.from_envvar('PLIVO_REST_CONFIG')
        # init logger
        self._init_logger()
        # create rest server
        fs_host, fs_port = self.app.config['FS_INBOUND_ADDRESS'].split(':', 1)
        fs_port = int(fs_port)
        fs_password = self.app.config['FS_PASSWORD']
        InboundEventSocket.__init__(self, fs_host, fs_port, fs_password, filter='ALL')
        # expose api functions to flask app
        for path, func_desc in urls.URLS.iteritems():
            func, methods = func_desc
            fn = getattr(self, func.__name__)
            self.app.add_url_rule(path, func.__name__, fn, methods=methods)
        # create wsgi server
        http_host, http_port = self.app.config['HTTP_ADDRESS'].split(':', 1)
        http_port = int(http_port)
        self.http_server = WSGIServer((http_host, http_port), self.app, log=self.logger)

    def _init_logger(self):
        logdebug = self.app.config.get('DEBUG', False)
        logtype = self.app.config.get('LOG_TYPE', 'stdout')
        if logtype == 'syslog':
            syslog_addr = self.app.config.get('SYSLOG_ADDRESS', '/dev/log')
            syslog_facility = self.app.config.get('SYSLOG_FACILITY', 'local0')
            self.logger = SysLogger(syslog_addr, syslog_facility)
        elif logtype == 'file':
            logfile = self.app.config.get('LOG_FILE', '/tmp/ivr.log')
            self.logger = FileLogger(logfile)
        else:
            self.logger = StdoutLogger()
        self.logger.name = self.name
        self.app._logger = self.logger
        if logdebug:
            self.logger.set_debug()
        else:
            self.logger.set_info()

    def start(self):
        # run
        #self.app.debug = True
        #self.app.run()
        #self.connect()
        self.http_server.serve_forever()


if __name__ == '__main__':
    server = RestServer(configfile='./restserver.conf')
    server.start()


