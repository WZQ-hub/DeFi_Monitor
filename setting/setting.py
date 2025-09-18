import logging

LOGGING = {
    'version': 1,
    'disable_existing_logger': False,

    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard'
        }
    },

    'loggers': {
        'test': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False
        }
    }
}