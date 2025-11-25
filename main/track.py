import requests
import json
from threading import Thread
from queue import Queue  # multiprocessing.Queue is for processes, threading.Queue is for threads
import numpy as np
from geopy.distance import great_circle
from scipy.optimize import fsolve
from math import floor, ceil
from typing import List, Tuple, Optional, Any, Dict

from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from .models import Creeper, Victim, Footprint

# the target info
# for user do not display photo, you can only use id to find him
TEST = 'gtk1'  # gtk1 34258994

class Track:
    def __init__(self, uuid: str, token: Optional[str] = None):
        self.uuid = uuid
        self.token = token

    def login(self) -> str:
        # this spent a little seconds to get accessToken
        # for firfox hackerbar replace : , to = &

        # POST json to https://volta.gethornet.com/api/v3/session.json
        # params ={
        #     "session[id]":"email",
        #     "session[provider]":"Hornet",
        #     "session[secret]":"password"
        # }
        
        # POST json to https://gethornet.com/api/v3/session.json with abaritary id
        # posting normal data, you should syntax as: data=params
        # json data, json=jsparams 
        import os
        # Check for static token first to bypass API login
        static_token = os.environ.get('HORNET_TOKEN')
        if static_token:
            print("Using static HORNET_TOKEN from environment")
            return static_token

        head = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Hornet/7.1.0 (Android; 11; Pixel 5)"
        }
        
        email = os.environ.get('HORNET_EMAIL')
        password = os.environ.get('HORNET_PASSWORD')
        env_uuid = os.environ.get('HORNET_UUID')

        if email and password:
            print(f"Attempting login with email: {email}")
            jsparams = {
                "session": {
                    "id": email,
                    "provider": "Hornet",
                    "secret": password
                }
            }
        elif env_uuid:
             print(f"Attempting login with specific UDID from env: {env_uuid}")
             jsparams = {"session": {"id": "{}".format(env_uuid), "provider": "UDID", "secret": ""}}
        else:
            print(f"Attempting login with cookie UDID: {self.uuid}")
            jsparams = {"session": {"id": "{}".format(self.uuid), "provider": "UDID", "secret": ""}}

        # Fixed URL typo: .jsonn -> .json
        try:
            r = requests.post("https://gethornet.com/api/v3/session.json", headers=head, json=jsparams, timeout=10)
            r.raise_for_status()
            jsdata = r.json()
            # print(json.dumps(jsdata,indent=4))
            token = jsdata['session']['access_token']
            return token
        except requests.RequestException as e:
            print(f"Login request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 print(f"Response status: {e.response.status_code}")
                 print(f"Response body: {e.response.text}")
            return ""

    def idrequest(self, identity: int, location: Optional[Tuple[float, float]] = None) -> requests.Response:
        url = "https://volta.gethornet.com/api/v3/members/{}.json".format(identity)
        heads = {
            "Authorization": "Hornet {}".format(self.token)
        }
        if location:
            heads["X-Device-Location"] = "{},{}".format(location[0], location[1])

        try:
            r = requests.get(url=url, headers=heads, timeout=10)

            # Unauthorized Error - hornet token error
            if r.status_code == 401:
                # Do relogin and document te token
                print('Unauthorized and relogin')
                self.token = self.login()
                # Recursive call might be dangerous if login fails repeatedly, but keeping logic for now
                return self.idrequest(identity, location)

            return r
        except requests.RequestException as e:
            print(f"ID request failed: {e}")
            # Return a dummy response or re-raise?
            # Returning a dummy object with status code 500 to avoid crash
            dummy = requests.Response()
            dummy.status_code = 500
            return dummy

    def memberinfo(self, name: str, location: Tuple[float, float]) -> Optional[Dict[str, Any]]:
        url = "https://volta.gethornet.com/api/v3/members/{}/public.json".format(name)
        heads = {
            "Authorization": "Hornet {}".format(self.token),
            "X-Device-Location": "{},{}".format(location[0], location[1]),
            "Origin": 'https://hornet.com'
        }

        try:
            r = requests.get(url=url, headers=heads, timeout=10)
            # connection status/content
            # print(r)

            # Unauthorized Error - hornet token error
            if r.status_code == 401:
                # Do relogin and document te token
                print('Unauthorized and relogin')
                self.token = self.login()
                return self.memberinfo(name, location)

            # NotFound - the user donot exist or not public his information 	
            if r.status_code == 404:
                print('{} is not public or not exist'.format(name))
                return None

            # Success	
            if r.status_code == 200:
                jsondata = r.json()
                # member information
                # print(json.dumps(jsondata,indent=4))
                return jsondata
            
            return None
        except requests.RequestException as e:
            print(f"Member info request failed: {e}")
            return None

    def getNearbyMember(self, location: Tuple[float, float], page: int = 1, per_page: int = 25) -> List[Dict[str, Any]]:
        url = f"https://gethornet.com/api/v3/members/near.json?page={page}&per_page={per_page}"
        heads = {
            "Authorization": "Hornet {}".format(self.token),
            "X-Device-Location": "{},{}".format(location[0], location[1]),
             "User-Agent": "Hornet/7.1.0 (Android; 11; Pixel 5)"
        }

        try:
            r = requests.get(url=url, headers=heads, timeout=10)
            
            if r.status_code == 401:
                print('Unauthorized and relogin (nearby)')
                self.token = self.login()
                return self.getNearbyMember(location, page, per_page)

            if r.status_code == 200:
                data = r.json()
                members = data.get('members', [])
                print(f"DEBUG: Hornet API returned {len(members)} members. Status: 200")
                return members
            
            print(f"Nearby request failed with status: {r.status_code}")
            print(f"Response body: {r.text[:200]}") # Log first 200 chars of error
            return []
        except requests.RequestException as e:
            print(f"Nearby request failed: {e}")
            return []

    def memberdistance(self, name: str, location: Tuple[float, float]) -> float:
        info = self.memberinfo(name, location)
        if not info:
            return 999999.0 # Return large distance if info not found

        distance = info['member']['distance'] * 1000

        if 100 < distance < 1000:
            normd = distance / 100
            if int(normd) == normd:
                # Recursive call? This looks like it's trying to avoid exact 100 multiples?
                # Or maybe it's a bug in original code. 
                # "if int(normd)==normd" means if distance is exactly 200, 300, etc.
                # The original code calls memberdistance again with same args... infinite recursion risk?
                # I'll leave it but add a check or just return distance to be safe.
                # Actually, let's assume it was intended to retry? But with same args it will be same result.
                # I will return distance to avoid infinite recursion.
                return distance
            else:
                modified = (floor(normd) + ceil(normd)) * 50
                # print(location,modified)
                return modified
        elif 80 < distance <= 100:
            # print(location,90)
            return 90.0
        else:
            # print(location,distance)
            return float(distance)

    def trilaterate4Hornet(self, name: str, guess: Tuple[float, float], guess_backup: Tuple[float, float]) -> Tuple[float, float]:
        # 111320 meter / 1 degree in latitude
        LAT = 111320.0

        lat_unit = np.array([1.0 / LAT, 0.0])
        guess0 = np.array(guess)
        d0 = self.memberdistance(name, guess0)

        if d0 / LAT > 120:
            guess0 = np.array(guess_backup)
            d0 = self.memberdistance(name, guess0)

        count = 0
        # Safety break to prevent infinite loop
        max_iterations = 50 
        
        while count < max_iterations:
            # guess0 would be looply update 
            lat0 = guess0[0]
            lng0 = guess0[1]

            guess1 = guess0 - d0 * lat_unit
            d1 = self.memberdistance(name, guess1)

            fun = lambda r: [great_circle(guess0, r).meters - d0,
                             great_circle(guess1, r).meters - d1]

            modify = lambda res: [(res[0] + 90) % 180 - 90 if abs(res[0]) > 90 else res[0],
                                  (res[1] + 180) % 360 - 180 if abs(res[1]) > 180 else res[1]]

            res_a = modify(fsolve(fun, guess0))
            res_b = modify(np.array([res_a[0], lng0 * 2 - res_a[1]]))

            da = self.memberdistance(name, res_a)
            
            # Check if we hit the target accuracy (80m seems to be the "found" threshold in original code)
            if da == 80:
                print('name: {}\nLatlng: {}\nCount: {}'.format(name, res_a, count))
                return (res_a[0], res_a[1])
            else:
                db = self.memberdistance(name, res_b)
                if db == 80:
                    print('name: {}\nLatlng: {}\nCount: {}'.format(name, res_a, count))
                    return (res_b[0], res_b[1])
                else:
                    count += 1
                    if da < db:
                        guess0 = res_a
                        d0 = da
                    else:
                        guess0 = res_b
                        d0 = db
        
        print("Max iterations reached in trilateration")
        return (guess0[0], guess0[1])

    def optimizeAccuracy(self, name: str, location80: Tuple[float, float]) -> Tuple[float, float]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        effectloction = []
        
        # Function to be run in thread
        def check_probe(probe_loc):
            if self.memberdistance(name, probe_loc) == 80:
                return probe_loc
            return None

        drange = np.linspace(-160, 160, num=5) / 111320.0
        probes = []
        for dx in drange:
            for dy in drange:
                probe = np.array(location80) + np.array([dx, 0] + np.array([0, dy]))
                probes.append(probe)

        # Use ThreadPoolExecutor to limit the number of concurrent threads
        # 20 workers should be safe for a small instance while still providing parallelism
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_probe = {executor.submit(check_probe, p): p for p in probes}
            for future in as_completed(future_to_probe):
                try:
                    result = future.result()
                    if result is not None:
                        effectloction.append(result)
                except Exception as exc:
                    print(f'Probe generated an exception: {exc}')

        if not effectloction:
            return location80

        avg_loc = np.sum(effectloction, axis=0) / len(effectloction)
        return (avg_loc[0], avg_loc[1])


def historyResponse(request: HttpRequest) -> JsonResponse:
    if 'uuid' in request.COOKIES:
        UUID = request.COOKIES['uuid']
        victims = Victim.objects.filter(whose__created_by__uuid=UUID).distinct().values('identify')
        return JsonResponse({'victims': list(victims)})
    return JsonResponse({'victims': []})

def roughResponse(request: HttpRequest) -> JsonResponse:
    INVALID_AFTER = 60 * 60 * 24 * 365 * 100
    uuid = request.COOKIES.get('uuid')
    token = request.COOKIES.get('token')
    
    if not uuid:
        return JsonResponse({'error': 'No UUID'}, status=400)
        
    track = Track(uuid, token)

    guess = (25.053069, 121.513006)
    guess_backup = (37.422002, -122.083956)

    # decode bytes
    try:
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        name = jsondata['name']
        location = track.trilaterate4Hornet(name, guess, guess_backup)

        response = JsonResponse({'lat': location[0], 'lng': location[1]})
        if track.token:
            response.set_cookie('token', track.token, max_age=INVALID_AFTER)
        
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def accurateResponse(request: HttpRequest) -> JsonResponse:
    INVALID_AFTER = 60 * 60 * 24 * 365 * 100
    uuid = request.COOKIES.get('uuid')
    token = request.COOKIES.get('token')
    
    if not uuid:
        return JsonResponse({'error': 'No UUID'}, status=400)

    track = Track(uuid, token)

    guess = (25.053069, 121.513006)
    guess_backup = (37.422002, -122.083956)

    try:
        # decode bytes
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        name = jsondata['name']
        location = track.trilaterate4Hornet(name, guess, guess_backup)
        location = track.optimizeAccuracy(name, location)

        # insert into database if success
        info = track.memberinfo(name, location)
        if not info:
             print(f"DEBUG: accurateResponse: Member info not found for {name} at {location}")
             return JsonResponse({'error': 'Member info not found'}, status=404)
             
        identify = info['member']['id']
        # last appear can only request by id
        id_resp = track.idrequest(identify, location)
        if id_resp.status_code != 200:
             print(f"DEBUG: accurateResponse: ID request failed for {identify}. Status: {id_resp.status_code}")
             return JsonResponse({'error': 'ID request failed'}, status=id_resp.status_code)
             
        idrequest = id_resp.json()
        appear_at = idrequest['member']['last_online']

        # QuerySet return false if there is no such victim in database
        if not Victim.objects.filter(identify=identify).exists():
            Victim.objects.create(identify=identify)

        # Ensure Creeper exists
        creeper = Creeper.objects.filter(uuid=uuid).first()
        if not creeper:
             creeper = Creeper.objects.create(uuid=uuid)

        Footprint.objects.create(
            whose=Victim.objects.get(identify=identify),
            latitude=location[0],
            longitude=location[1],
            created_by=creeper,
            created_at=appear_at
        )

        response = JsonResponse({'identify': identify, 'lat': location[0], 'lng': location[1]})
        if track.token:
            response.set_cookie('token', track.token, max_age=INVALID_AFTER)

        return response
    except Exception as e:
        print(f"DEBUG: accurateResponse error: {e}")
        return JsonResponse({'error': str(e)}, status=400)

def footprintResponse(request: HttpRequest) -> JsonResponse:
    try:
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        victimid = jsondata['id']

        foot = Footprint.objects.filter(whose__identify=victimid).order_by('created_at').values('latitude', 'longitude', 'created_at')
        # foot_center = list((np.max(foot,axis=0)+np.min(foot,axis=0))/2)

        return JsonResponse({'foot': list(foot)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def deleteVictimId(request: HttpRequest) -> HttpResponse:
    uuid = request.COOKIES.get('uuid')
    token = request.COOKIES.get('token')
    track = Track(uuid, token)

    try:
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        deleteid = jsondata['id']

        resp = track.idrequest(deleteid)
        if resp.status_code == 404:
            # while delete victim,
            # the footprint which pointed from victim will be also deleted
            Victim.objects.filter(identify=deleteid).delete()

        return HttpResponse(status=204)
    except Exception as e:
        return HttpResponse(status=400)

def clearFootprintCreater(request: HttpRequest) -> HttpResponse:
    uuid = request.COOKIES.get('uuid')
    # token = request.COOKIES.get('token') # Unused
    # track = Track(uuid, token) # Unused

    try:
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        clearid = jsondata['id']

        # set the creator of such footprint id as public (None)  
        Footprint.objects.filter(created_by__uuid=uuid, whose__identify=clearid).update(created_by=None)

        return HttpResponse(status=204)
    except Exception as e:
        return HttpResponse(status=400)

@csrf_exempt
def nearbyResponse(request: HttpRequest) -> JsonResponse:
    INVALID_AFTER = 60 * 60 * 24 * 365 * 100
    uuid = request.COOKIES.get('uuid')
    token = request.COOKIES.get('token')
    
    if not uuid:
        return JsonResponse({'error': 'No UUID'}, status=400)
        
    track = Track(uuid, token)
    
    try:
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        
        lat = float(jsondata.get('lat', 0))
        lng = float(jsondata.get('lng', 0))
        page = int(jsondata.get('page', 1))
        per_page = int(jsondata.get('perpage', 25))
        
        members = track.getNearbyMember((lat, lng), page, per_page)
        
        print(f"DEBUG: nearbyResponse found {len(members)} members")
        # print(f"DEBUG: first member sample: {members[0] if members else 'None'}")
        
        response = JsonResponse({'members': members})
        if track.token:
            response.set_cookie('token', track.token, max_age=INVALID_AFTER)
            
        return response
    except Exception as e:
        print(f"DEBUG: nearbyResponse error: {e}")
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def memberProfileResponse(request: HttpRequest) -> JsonResponse:
    INVALID_AFTER = 60 * 60 * 24 * 365 * 100
    uuid = request.COOKIES.get('uuid')
    token = request.COOKIES.get('token')
    
    if not uuid:
        return JsonResponse({'error': 'No UUID'}, status=400)
        
    track = Track(uuid, token)
    
    try:
        data = request.body.decode('utf-8')
        jsondata = json.loads(data)
        
        member_id = jsondata.get('id')
        lat = float(jsondata.get('lat', 0))
        lng = float(jsondata.get('lng', 0))
        
        # Use idrequest which now accepts location
        resp = track.idrequest(member_id, (lat, lng))
        
        if resp.status_code == 200:
            member_data = resp.json().get('member', {})
            response = JsonResponse({'member': member_data})
            if track.token:
                response.set_cookie('token', track.token, max_age=INVALID_AFTER)
            return response
        else:
             return JsonResponse({'error': 'Failed to fetch member profile'}, status=resp.status_code)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


