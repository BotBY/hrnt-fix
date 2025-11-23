from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from .models import Victim, Creeper
from .track import Track
from user_agents import parse
import uuid

def index(request: HttpRequest) -> HttpResponse:
    #  in cookie based: request.COOKIES['uuid']
    #                   response.set_cookie('uuid',UUID)

    response = None
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    agent = parse(user_agent_string)

    if 'uuid' not in request.COOKIES or not Creeper.objects.filter(uuid=request.COOKIES['uuid']).exists():
        INVALID_AFTER = 60 * 60 * 24 * 365 * 100
        template_name = 'index.html' if agent.is_pc else 'legacy-index.html'
        response = render(request, template_name)
        
        new_uuid = uuid.uuid1().hex
        # Note: Track.login() might fail if credentials aren't set up, handling gracefully would be better
        # but keeping original logic for now.
        # Ideally we shouldn't be logging in on every new user visit if it's a shared account?
        # The original code creates a new Track instance and logs in.
        try:
            token = Track(new_uuid).login()
        except Exception as e:
            print(f"Login failed: {e}")
            token = "error_token"

        response.set_cookie('uuid', new_uuid, max_age=INVALID_AFTER)
        response.set_cookie('token', token, max_age=INVALID_AFTER)
        Creeper.objects.create(uuid=new_uuid)
    else:
        current_uuid = request.COOKIES['uuid']
        #  too powerful and clean!!? 
        #  double underline foreign to whose and again foreign to created_by ...
        victims = Victim.objects.filter(whose__created_by__uuid=current_uuid).distinct()
        template_name = 'index.html' if agent.is_pc else 'legacy-index.html'
        response = render(request, template_name, {'victims': victims})

    return response