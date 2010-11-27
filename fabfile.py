# -*- coding: utf-8 -*-
"""
    fabfile.py
    ~~~~~~~~~~
    
    fabfile to generate html and upload to a remote web server using ssh.
    
    :copyright: (c) 2010 by Rafael Goncalves Martins
    :license: BSD (http://www.opensource.org/licenses/bsd-license.php)
"""

from fabric.api import env, local, put, run
from glob import glob

env.user = 'rafaelmartins'
env.hosts = ['dev.gentoo.org']

def clean():
    local('rm -rf _build', capture=False)

def build():
    clean()
    local('mkdir -p _build', capture=False)
    for f in [i[len('config/'):-len('.ini')] for i in glob('config/*.ini')]:
        local('python checkbump.py config/%s.ini > _build/%s.html' % (f, f), capture=False)

def upload():
    run('mkdir -p public_html/checkbump')
    for html_file in glob('_build/*.html'):
        put(html_file, 'public_html/checkbump')
