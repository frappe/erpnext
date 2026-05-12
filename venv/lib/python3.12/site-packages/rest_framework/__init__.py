r"""
______ _____ _____ _____    __
| ___ \  ___/  ___|_   _|  / _|                                           | |
| |_/ / |__ \ `--.  | |   | |_ _ __ __ _ _ __ ___   _____      _____  _ __| |__
|    /|  __| `--. \ | |   |  _| '__/ _` | '_ ` _ \ / _ \ \ /\ / / _ \| '__| |/ /
| |\ \| |___/\__/ / | |   | | | | | (_| | | | | | |  __/\ V  V / (_) | |  |   <
\_| \_\____/\____/  \_/   |_| |_|  \__,_|_| |_| |_|\___| \_/\_/ \___/|_|  |_|\_|
"""

import django

__title__ = 'Django REST framework'
__version__ = '3.14.0'
__author__ = 'Tom Christie'
__license__ = 'BSD 3-Clause'
__copyright__ = 'Copyright 2011-2019 Encode OSS Ltd'

# Version synonym
VERSION = __version__

# Header encoding (see RFC5987)
HTTP_HEADER_ENCODING = 'iso-8859-1'

# Default datetime input and output formats
ISO_8601 = 'iso-8601'


if django.VERSION < (3, 2):
    default_app_config = 'rest_framework.apps.RestFrameworkConfig'


class RemovedInDRF315Warning(PendingDeprecationWarning):
    pass
