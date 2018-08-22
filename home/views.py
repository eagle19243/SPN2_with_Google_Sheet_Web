# -*- coding: utf-8 -*-
import re
import json
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2client import client
from celery.result import AsyncResult
from home.tasks import process_doc

CLIENT_ID = '993382127942-iakt5sui2m26t4vg0ed1g7f0kt2kch4e.apps.googleusercontent.com'
CLIENT_SECRET = '3JrJxLpmpkN3WezmwYKF4AhL'
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
REDIRECT_URI_DEV = 'http://localhost:8092/archive/'
REDIRECT_URI_PROD = 'http://anton-dev.us.archive.org:8092/archive/'

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def archive(request):
    if request.method == 'POST':
        spreadsheet_id = get_spreadsheet_id_from_url(request.POST['google_sheet_url'])
        s3_access_key = request.POST['access_key']
        s3_secret_key = request.POST['secret_key']

        if not spreadsheet_id:
            return HttpResponse(json.dumps({'success': False, 'message': 'Invalid Spreadsheet URL'}))
        else:
            auth_code = request.COOKIES.get('auth_code')
            job = process_doc.delay(spreadsheet_id, auth_code, {
                'User-Agent': 'Wayback_Machine_SPN2_Google_Spreadsheet',
                'Accept': 'application/json',
                'authorization': 'LOW %s:%s' % (s3_access_key, s3_secret_key)
            })

            return JsonResponse({'success': True, 'job': job.id})

    else:
        if 'code' in request.GET:
            code = request.GET['code']
            response = render(request, 'archive.html', {'message': 'Processing...'})
            response.set_cookie('auth_code', code)
            return response
        else:
            return HttpResponseRedirect(get_auth_uri())

def get_progress(request):
    if 'job' in request.GET:
        job_id = request.GET['job']
    else:
        return HttpResponse('No job id give.')

    job = AsyncResult(job_id)
    data = job.result or job.state

    return HttpResponse(json.dumps(data))

def get_spreadsheet_id_from_url(url):
    match = re.match(r'https:\/\/docs\.google\.com\/spreadsheets\/d\/(.*)\/edit', url)
    if match:
        return match.groups()[0]
    else:
        return None

def get_auth_uri():
    flow = client.OAuth2WebServerFlow(CLIENT_ID,
                                      CLIENT_SECRET,
                                      SCOPES,
                                      REDIRECT_URI_PROD)
    auth_uri = flow.step1_get_authorize_url()
    return auth_uri
