#!/usr/bin/env python
"""
Test the raw parsing functionality directly
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from tracker.views_new import _handle_raw_announce
from django.test import RequestFactory

# Create a mock request with the raw query string that transmission would send
factory = RequestFactory()
raw_query = 'info_hash=%60%DE%F56%27%1Ei%8ET%D6%B7%9F%A0%5D%5DZ%E9%D7q%93&peer_id=-TR4000-abcdefghijkl&port=51413&uploaded=0&downloaded=0&left=9772752&compact=1&event=started'

# Create request object
request = factory.get('/announce?' + raw_query)
request.META['QUERY_STRING'] = raw_query

print(f"Testing raw parsing with query: {raw_query[:100]}...")

try:
    response = _handle_raw_announce(raw_query, request)
    print(f"Success! Response type: {type(response)}")
    print(f"Response content: {response.content[:200]}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
