
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
import re
from operator import add
from time import time
from django.db import connection
import unicodedata

try:
    import cPickle as pickle
except ImportError:
    import pickle

import base64

regexp = re.compile(r'(?P<cmt><!--\s*STATS:(?P<fmt>.*?)-->)')

class StatsMiddleware(object):
    """ Inspiration from http://davidavraamides.net/blog/2006/07/03/page-stats-middleware/"""

    def process_request(self, request):
        request.start_time = time()
        request._num_queries = len(connection.queries)

    def process_response(self, request, response):
        # Hack to prevent processing of static files -- aseering 10/20/2010
        if request.path.startswith("/media/"):
            return response

        from django.conf import settings
        debug = settings.DEBUG

        try:
            totTime = time() - request.start_time
        except AttributeError:
            totTime = -1

        stats = {
            'totTime': totTime,
            'dbInfo': ''
            }

        if debug:
            if not hasattr(request, "_num_queries"):
                request._num_queries = 0
            # compute the db time for the queries just run
            queries = len(connection.queries) - request._num_queries
            if queries:
                dbTime = reduce(add, [float(q['time']) 
                                      for q in connection.queries[request._num_queries:]])
            else:
                dbTime = 0.0

            # and backout python time
            pyTime = totTime - dbTime

            stats['dbInfo'] = ' Code: %(pyTime).2fs DB: %(dbTime).2fs Queries: %(queries).d' \
                              %  {'pyTime': pyTime,
                                  'dbTime': dbTime,
                                  'queries':queries}


        # replace the comment if found            
        if response and response.content:
            s = response.content
            match = regexp.search(s)
            if match:
                s = s[:match.start('cmt')] + \
                    match.group('fmt') % stats + \
                    s[match.end('cmt'):]
                response.content = s

        if settings.DISPLAYSQL and settings.DEBUG and \
           request.META['REMOTE_ADDR'] in settings.INTERNAL_IPS:

            sqlcontent = ''.join("\n"+'%s:&nbsp;&nbsp;%s<br />' % \
                              (q['time'], q['sql']) for q in connection.queries)

            sqlcontent = unicodedata.normalize('NFKD', unicode(sqlcontent)).encode('ascii', 'ignore')
            
            if '</body>' in response.content.lower():
                pos = response.content.find('</body>')
                response.content = '%s\n\n<div class="sql">\n%s\n\n</div>%s' % \
                                   (response.content[:pos], sqlcontent, response.content[pos:])

        return response

