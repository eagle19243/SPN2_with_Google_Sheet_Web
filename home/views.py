# -*- coding: utf-8 -*-
import re
import time
import requests
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file as oauth_file, client, tools

SPN_URL = 'http://vbanos-dev.us.archive.org:8092/save/'
AVAILABILITY_API_URL = 'https://archive.org/wayback/available'
CLIENT_ID = '993382127942-iakt5sui2m26t4vg0ed1g7f0kt2kch4e.apps.googleusercontent.com'
CLIENT_SECRET = '3JrJxLpmpkN3WezmwYKF4AhL'
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
REDIRECT_URI_DEV = 'http://localhost:8000/archive'
REDIRECT_URI_PROD = 'http://anton-dev.us.archive.org:8092/archive'

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def archive(request):
    if request.method == 'POST':
        spreadsheet_id = get_spreadsheet_id_from_url(request.POST['google_sheet_url'])
        s3_access_key = request.POST['access_key']
        s3_secret_key = request.POST['secret_key']

        if not spreadsheet_id:
            return JsonResponse({'success': False, 'message': 'Invalid Spreadsheet URL'})
        else:
            auth_code = request.COOKIES.get('auth_code')
            process_doc(spreadsheet_id, auth_code, {
                'User-Agent': 'Wayback_Machine_SPN2_Google_Spreadsheet',
                'Accept': 'application/json',
                'authorization': 'LOW %s:%s' % (s3_access_key, s3_secret_key)
            })

            return JsonResponse({'success': True})

    else:
        if 'code' in request.GET:
            code = request.GET['code']
            response = render(request, 'archive.html', {'message': 'Processing...'})
            response.set_cookie('auth_code', code)
            return response
        else:
            return HttpResponseRedirect(get_auth_uri())

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
                                      REDIRECT_URI_DEV)
    auth_uri = flow.step1_get_authorize_url()
    return auth_uri

def process_doc(spreadsheet_id, auth_code, headers):
    flow = client.OAuth2WebServerFlow(CLIENT_ID,
                                      CLIENT_SECRET,
                                      SCOPES,
                                      REDIRECT_URI_DEV)
    creds = flow.step2_exchange(auth_code)
    service = build('sheets', 'v4', http=creds.authorize(Http()))

    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = [s['properties']['title'] for s in spreadsheet['sheets']]

    for sheet in sheets:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet + '!A3:A1000').execute()
        values = result.get('values', [])

        if not values:
            print('No data found in ', sheet)
        else:
            row_index = 2
            for value in values:
                row_index = row_index + 1
                url = value[0]

                if not is_valid_url(url):
                    continue

                availability = check_availability(url, headers)
                job_id = request_capture(url, headers)

                if not job_id:
                    continue

                (status, captured_url) = request_capture_status(job_id, headers)

                update_values(service,
                              spreadsheet_id,
                              sheet + '!B' + str(row_index) + ':D'+ str(row_index),
                              [availability, status, captured_url])

def update_values(service, spreadsheet_id, range, values):
    body = {
        'values':[values]
    }
    service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, valueInputOption='RAW',
                                           range=range, body=body).execute()

def is_valid_url(url):
    match = re.match(r'(ftp|http|https):\/\/(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?', url)
    return match is not None

def request_capture(url, headers):
    response = requests.get(url=SPN_URL + url, headers=headers)

    try:
        data = response.json()
        return data['job_id']
    except:
        return None

def request_capture_status(job_id, headers):
    time.sleep(10)
    response = requests.get(
        url='%sstatus/%s?_t=%s' % (SPN_URL, job_id, str(time.time())),
        headers=headers
    )

    try:
        data = response.json()
        if data['status'] == 'pending':
            return request_capture_status(job_id, headers)
        else:
            if 'timestamp' in data and 'original_url' in data:
                return (data['status'], 'http://web.archive.org/web/' + data['timestamp'] + '/' + data['original_url'])
            else:
                return (data['status'], '')
    except:
        return('Error: JSON parse', '')

def check_availability(url, headers):
    response = requests.get(url=AVAILABILITY_API_URL + '?url=' + url, headers=headers)

    if get_wayback_url_from_response(response.json()):
        return True

    return False

def get_wayback_url_from_response(json):
    ret = None

    if (json and
        json['archived_snapshots'] and
        json['archived_snapshots']['closest'] and
        json['archived_snapshots']['closest']['available'] and
        json['archived_snapshots']['closest']['available'] == True and
        json['archived_snapshots']['closest']['status'] == '200' and
        is_valid_url(json['archived_snapshots']['closest']['url'])):

        ret = make_https(json['archived_snapshots']['closest']['url'])

    return ret

def make_https(url):
    return url.replace('http:', 'https:')
