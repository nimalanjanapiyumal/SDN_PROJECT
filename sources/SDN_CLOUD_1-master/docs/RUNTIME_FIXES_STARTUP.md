Startup fixes included in this package:
- manage.sh no longer crashes with `name: unbound variable`
- controller logs now report a clear message if no log file exists yet
- controller environment check suppresses Eventlet deprecation warnings
- controller launcher suppresses Eventlet deprecation warnings during startup

Run sequence:
  bash manage.sh fix-perms
  bash manage.sh controller bootstrap
  bash manage.sh controller start
  bash manage.sh controller logs
