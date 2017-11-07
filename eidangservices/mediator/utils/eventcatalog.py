# -*- coding: utf-8 -*-
"""

EIDA Mediator

This file is part of the EIDA mediator/federator webservices.

"""

import io
import os
import re
import uuid

from operator import itemgetter

import obspy

from eidangservices.mediator.server import httperrors


# IDs from SC3 that do not validate against QuakeML 1.2_
# - arrival publicIDs from ETHZ (replace all publicIDs)
# - filterID
# - pickID (OK from ETHZ but may be invalid elsewhere)
RE_EVENT_XML_PUBLIC_ID = (
    re.compile(r'publicID="(.+?)"'), re.compile(r'publicID=\'(.+?)\''),
    re.compile(r'<filterID>(.+?)<\/filterID>'), 
    re.compile(r'<pickID>(.+?)<\/pickID>'))

PUBLIC_ID_LOCAL_PREFIX = 'smi:local/'


def get_obspy_catalog(cat_xml):
    """
    Read QuakeML document into ObsPy catalog object. Sanitize broken
    IDs. Return catalog object and ID replacement map.
    
    """
        
    # replace all publicIDs, pickIDs, filterIDs with sanitized ones
    # replace_map is a dict: {'replacement': 'original', ...}
    cat_xml, replace_map = sanitize_catalog_public_ids(cat_xml)
    #print cat_xml

    try:
        cat = obspy.read_events(cat_xml)
    except Exception, e:
        err_msg = "obspy catalog read failed: %s" % e
        raise RuntimeError, err_msg
    
    return cat, replace_map


def restore_catalog_to_file(outfile, cat, replace_map):
    """Restore replaced IDs in catalog and write to file."""
    
    if len(cat) == 0:
        return False
    
    else:
        print "writing filtered event catalog, %s events" % (len(cat))
                
        with io.BytesIO() as bf:
            cat.write(bf, format="QUAKEML")
                
            # replace sanitized publicIDs with original ones
            restored_cat_xml = restore_catalog_public_ids(bf, replace_map)
                
        with open(outfile, 'wb') as fh:
            fh.write(restored_cat_xml)
            
        return True
        
            
def sanitize_catalog_public_ids(cat_xml):
    """
    Replace all public IDs in a QuakeML instance with well-behaved
    place holders. Return string with replacements, and dict of original
    and replaced matches.
    
    """
    
    replace_list = []
    replace_map = {}
    
    # find public IDs in QuakeML instance and get random replacement
    for pattern in RE_EVENT_XML_PUBLIC_ID:
        for m in re.finditer(pattern, cat_xml):
            public_id = m.group(1)
            replacement = "%s%s" % (PUBLIC_ID_LOCAL_PREFIX, str(uuid.uuid4()))
            
            #print "replace %s with %s" % (public_id, replacement)
            replace_list.append(
                dict(orig=public_id, repl=replacement, start=m.start(1), 
                    end=m.end(1)))
                
            replace_map[replacement] = public_id
    
    # sort replace list by start index, descending
    replace_list = sorted(replace_list, key=itemgetter('start'), reverse=True)
    
    # replace public IDs by position (start at end of text so that indices are
    # not compromised)
    for match in replace_list:
        cat_xml = \
            cat_xml[:match['start']] + match['repl'] + cat_xml[match['end']:]
       
    return cat_xml, replace_map


def restore_catalog_public_ids(stream, replace_map):
    """Replace items from replace map in io stream."""
    
    text = stream.getvalue()
    
    # replacement strings are unique, so simple replace method can be used
    for repl, orig in replace_map.iteritems():
        text = text.replace(repl, orig)
    
    return text


def merge_catalogs(catalogs, replace_maps):
    """
    Merge a list of catalogs and replacement maps into one.
    TODO(fab)
    
    """
    if not catalogs:
        return catalogs, replace_maps
        
    else:
        cat = catalogs[0].copy()
        replace_map = replace_maps[0]
    
        for idx in xrange(1, len(catalogs)):
            cat += catalogs[idx]
            replace_map.update(replace_maps[idx])
    
    return cat, replace_map

