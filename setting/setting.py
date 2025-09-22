LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

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
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'filename': '/Users/super_wzq/PycharmProjects/spider/logs/web3.log',
            'encoding': 'UTF-8',
            'mode': 'a'
        }
    },

    'loggers': {
        'test': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False
        },
        'web3': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False
        }
    }
}