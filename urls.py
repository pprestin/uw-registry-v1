from django.conf.urls.defaults import *

urlpatterns = patterns('uwregistry',
    (r'^$', 'views.home'),
    (r'^service/add/$', 'views.submit'),
    (r'^(?P<nick>[-\w]+)/$', 'views.home'),
)
