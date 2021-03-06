from django.http import HttpResponse, HttpResponseRedirect,HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django import template
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.decorators.cache import never_cache
from django.db.models import Q
from uwregistry.forms import *
from uwregistry.models import Service
from uwregistry.rss import RSS
from uwregistry.user_voice import UserVoice
from datetime import datetime
from django.core.mail import mail_admins
from django.conf import settings
import sys


def home(request):
    top_services = Service.objects.order_by('-date_submitted').filter(status=Service.APPROVE_STAT)[:10]
    return render_to_response(
            "index.html",
            {
                'services' : top_services,
	        },
            RequestContext(request)
    )

@never_cache
def user_voice_view(request):
    user_voice = None
    try:
        user_voice = UserVoice()
        user_voice.retrieve_data()
    except:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return HttpResponseServerError()
    return render_to_response(
            "uservoice.html",
            {
                'uservoice' : user_voice
	        },
            RequestContext(request)
    )

@never_cache
def rss_view(request):
    return render_to_response(
            "rss.html",
            {
                'rss' : RSS()
	        },
            RequestContext(request)
    )

#@never_cache
def learn(request):
    return render_to_response(
        "learn.html"
        )

def discover(request):
    upcoming_services = Service.objects.filter(status=Service.APPROVE_STAT).order_by('date_submitted').reverse().filter(in_development=True)
    user_voice = UserVoice()
    user_voice.retrieve_data_for_all()
    
    return render_to_response("discover.html",
        {
          'upcoming_services': upcoming_services,
          'user_voice': user_voice
        },
        RequestContext(request)
        )

def connect(request):
    return HttpResponseRedirect('/service/browse')

def service(request, nick):
    #service must have this nick and be approved:
    service = get_object_or_404(Service, nickname__iexact=nick, status=Service.APPROVE_STAT)
    service_user_voice = UserVoice( nickname=nick, service=service )
    return render_to_response(
            "service.html",
            {
                'service' : service, 
				'uservoice' : service_user_voice, 
				'uservoice_url' : settings.USER_VOICE_URL,
            },
            RequestContext(request))

def render_service_list(request,template,args={}):
    search_name = request.GET.get('search')

    services_list = Service.objects.extra(select={'lower_name': 'lower(name)'}).order_by('lower_name').filter(status=Service.APPROVE_STAT)

    if search_name != None:
        services_list = services_list.filter(Q(name__contains = search_name) | Q(nickname__contains = search_name))

    paginator = Paginator(services_list, 10)
    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        services = paginator.page(page)
    except (EmptyPage, InvalidPage):
        services = paginator.page(paginator.num_pages)

    base_args = {
        'services' : services,
        'search': search_name,
    }

    base_args.update(args)
    
    return render_to_response(template, base_args, context_instance=RequestContext(request))

def browse(request):
    return render_service_list(request,"browse.html",{'uservoice_url' : settings.USER_VOICE_URL})

def search(request):
    return render_service_list(request,"service_list.html")

def whatsnext(request):
    services = Service.objects.filter(status=Service.APPROVE_STAT).order_by('date_submitted').reverse().filter(in_development=True)

    return render_to_response("whatsnext.html", {
        'services' : services,
        }, context_instance=RequestContext(request))


def recent_activity(request):
    services = Service.objects.filter(status=Service.APPROVE_STAT).order_by('date_modified').reverse()

    return render_to_response("recent.html", {
        'services' : services,
        }, context_instance=RequestContext(request))


@login_required
def mine(request):
    my_services = Service.objects.filter(owner=request.user)
    return render_to_response("mine.html", {
        'services' : my_services,
        }, RequestContext(request))
 

@login_required
def edit(request, nick):
    service = get_object_or_404(Service, nickname=nick, owner=request.user)
    if request.method == 'POST':
        form = ServiceEditForm(instance=service, data=request.POST)
        if form.is_valid():
            form.save(commit=False)
            service.date_modified = datetime.now()
            service.save()
            request.user.message_set.create(message='Service updated.')
            return HttpResponseRedirect('/service/mine/')
    else:
        form = ServiceEditForm(instance=service)

    return render_to_response(
            "submit.html", 
            {
                'form' : form,
            }, 
            RequestContext(request))

 

@login_required
def submit(request):

    if request.method == 'POST':
        form = ServiceForm(data=request.POST)

        if form.is_valid():
            service = form.save(commit=False)
            service.owner = request.user
            service.status = service.SUBMIT_STAT
            service.date_submitted = datetime.now()
            service.date_modified = datetime.now()
            service.save()
            request.user.message_set.create(message='Your service has been submitted for moderation.')
            subject = 'New service "%s" submitted to the registry' % service.name
            body = 'Please go to http://webservices.washington.edu/admin/uwregistry/service/%d to review it' % service.id
            try:
                mail_admins(subject, body, fail_silently=False)
            except:
                sys.stderr.write("Email is failing!\n")
            return HttpResponseRedirect('/service/mine')
    else:
        form = ServiceForm()

    return render_to_response(
            "submit.html", 
            {
                'form' : form,
                'new' : True,
            }, 
            RequestContext(request))
