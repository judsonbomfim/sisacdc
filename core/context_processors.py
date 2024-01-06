import os
from django.conf import settings


def sis_version(request):
    return {'SIS_VERSION': settings.SIS_VERSION}