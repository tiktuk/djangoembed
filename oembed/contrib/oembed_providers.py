import Image
import os
import re

from django.conf import settings
from django.contrib.sites.models import Site

import oembed
from oembed.providers import BaseProvider
from oembed.resources import OEmbedResource
from oembed.utils import size_to_nearest, scale


class GoogleMapsProvider(BaseProvider):
    regex = r'^http://maps.google.com/maps\?([^\s]+)'
    provides = False
    resource_type = 'rich'
    
    MAP_SIZES = [(x, x) for x in xrange(100, 900, 100)]
    VALID_PARAMS = ['q', 'z']
    
    def request_resource(self, url, **kwargs):
        maxwidth = kwargs.get('maxwidth', None)
        maxheight = kwargs.get('maxheight', None)
        
        # calculate the appropriate width and height
        w, h = size_to_nearest(maxwidth, maxheight, self.MAP_SIZES, True)
        
        # prepare the dictionary of data to be returned as an oembed resource
        data = {
            'type': 'rich', 'provider_name': 'Google', 'version': '1.0',
            'width': w, 'height': h, 'title': '', 'author_name': '',
            'author_url': ''
        }
        
        url_params = re.match(self.regex, url).groups()[0]
        url_params = url_params.replace('&amp;', '&').split('&')
        
        map_params = ['output=embed']
        
        for param in url_params:
            k, v = param.split('=', 1)
            if k in self.VALID_PARAMS:
                map_params.append(param)
        
        data['html'] = '<iframe width="%d" height="%d" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" src="http://maps.google.com/maps?%s"></iframe>' % \
            (w, h, '&amp;'.join(map_params))
        
        return OEmbedResource.create(data)


class StaticMediaProvider(BaseProvider):
    media_url = settings.MEDIA_URL.strip('/')
    if not media_url.startswith('http'):
        all_domains = Site.objects.values_list('domain', flat=True)
        media_url = 'http://[^\s]*?(?:%s)/%s' % ('|'.join(all_domains), media_url)
    
    regex = re.compile(r'^%s/([^\s]+\.(jpg|gif|png))' % media_url, re.I)
    provides = False
    resource_type = 'photo'
    
    IMAGE_SIZES = [(x, x) for x in xrange(100, 900, 100)]
    
    def request_resource(self, url, **kwargs):
        maxwidth = kwargs.get('maxwidth', None)
        maxheight = kwargs.get('maxheight', None)
        
        # calculate the appropriate bounds for width and height
        w, h = size_to_nearest(maxwidth, maxheight, self.IMAGE_SIZES, True)

        # get the path, i.e. /media/img/kitties.jpg
        image_path = re.match(self.regex, url).groups()[0]
        
        # create the entire filename as it would be on disk
        filename = settings.MEDIA_ROOT + image_path
        
        # create the entire url as it would be on site, minus the filename
        base_url, ext = url.rsplit('.', 1)
                
        # create the file path on disk minus the extension
        base_file, ext = filename.rsplit('.', 1)
        
        append = '_%sx%s.%s' % (w, h, ext)
        
        new_filename = '%s%s' % (base_file, append)
        
        if not os.path.isfile(new_filename):
            # open the original to calculate its width and height
            img = Image.open(filename)
            img_width, img_height = img.size
            
            # do the math-y parts
            new_width, new_height = scale(img_width, img_height, w, h)
            
            img = img.resize((new_width, new_height), Image.ANTIALIAS)
            img.save(new_filename)
        
        new_url = '%s%s' % (base_url, append)
        
        # get just the filename, i.e. test.jpg - used for generated the title
        # of the returned oembed resource
        image_filename = image_path.rsplit('/', 1)[1]
        
        data = {'type': 'photo', 'provider_name': '', 'version': '1.0',
                'width': w, 'height': h, 'title': image_filename,
                'url': new_url, 'author_name': '', 'author_url': ''}
        
        return OEmbedResource.create(data)


oembed.site.register(GoogleMapsProvider)
oembed.site.register(StaticMediaProvider)
