import json
import boto3
import datetime as dt
from operator import itemgetter


def get_dates(direction, service=False):
    with open('dates.json') as f:
        table = json.load(f)
    if service:
        service = f'{direction}-{service}'
        dates = parse_list_dates(table[service], service)
    else:
        trash = parse_list_dates(table[f'{direction}-trash'], 'garbage')
        recycle = parse_list_dates(table[f'{direction}-recycle'], 'recycle')
        dates = (trash, recycle)
    return dates


def parse_list_dates(src, service):
    if isinstance(src, list):
        return [{'service': service, 'date': dt.datetime.strptime(d, '%Y-%m-%d').date()} for d in src]


def build_response(output, should_end_session):
    return {
        'version': '1.0',
        'sessionAttributes': {},
        'response': build_speech_response(output, should_end_session)
    }


def build_speech_response(output, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': 'Saratoga Garbage',
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': None
            }
        },
        'shouldEndSession': should_end_session
    }


def build_output_speech(_events):
    if len(_events) == 2:
        return "The next {} day is {} and {} day is {}".format(_events[0]['service'], _events[0]['date'], _events[1]['service'], _events[1]['date'])
    elif len(_events) == 1:
        return "The next {} day is {}".format(_events[0]['service'], _events[0]['date'])
    elif len(_events) == 0:
        return "No days within the next week."
    else:
        _out = 'The next '
        for x in _events:
            _out = _out + "{} is {} ".format(x['service'], x['date'])
        return _out


def get_day():
    today = dt.date.today()
    one_week = (today + dt.timedelta(days=7))
    trash_events, recycle_events = get_dates('north')
    trash_week = [event for event in trash_events if today <= event['date'] <= one_week]
    recycle_week = [event for event in recycle_events if today <= event['date'] <= one_week]
    _week = trash_week + recycle_week
    sorted_week = sorted(_week, key=itemgetter('date'))
    if len(sorted_week) > 2:
        sorted_week = sorted_week[:2]
    output = build_output_speech(sorted_week)
    return build_response(output, True)


def on_intent(request):
    intent = request['intent']
    intent_name = intent['name']

    if intent_name == 'GetDay':
        return get_day()
    elif intent_name in ['AMAZON.StopIntent', 'AMAZON.CancelIntent']:
        return build_response("Goodbye", True)
    elif intent_name == 'AMAZON.HelpIntent':
        return build_response("You can ask me when is garbage day or you can say exit... What can I help you with?", False)


def handler(event, context):
    ssm = boto3.client('ssm')
    app_id = ssm.get_parameter(Name='saratoga-garbage.prd.appid')['Parameter']['Value']
    if (event['session']['application']['applicationId'] != app_id):
        raise ValueError("Invalid Application ID")

    if event['request']['type'] == 'IntentRequest':
        return on_intent(event['request'])
    if event['request']['type'] == 'LaunchRequest':
        return get_day()
