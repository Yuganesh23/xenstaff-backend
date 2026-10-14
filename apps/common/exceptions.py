from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        customized_response = {
            'success': False,
            'status_code': response.status_code,
            'error': {
                'message': 'An error occurred during request processing.',
                'details': response.data
            }
        }
        if isinstance(response.data, dict) and 'detail' in response.data:
            customized_response['error']['message'] = response.data['detail']
            
        response.data = customized_response

    return response
