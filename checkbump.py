#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    checkbump.py
    ~~~~~~~~~~~~
    
    Version bump checker for Gentoo Linux packages.
    Depends on Jinja2.
    
    :copyright: (c) 2010 by Rafael Goncalves Martins
    :license: BSD (http://www.opensource.org/licenses/bsd-license.php)
"""

import os, sys

# force "~*" keywords
os.environ['ACCEPT_KEYWORDS'] = '~*'

# ignore overlays
os.environ['PORTDIR_OVERLAY'] = ''

from ConfigParser import ConfigParser
from contextlib import closing
from datetime import datetime
from jinja2 import Template
from logging import getLogger, Formatter, StreamHandler, INFO
from portage import portagetree
from portage.versions import pkgsplit, vercmp
from subprocess import Popen, PIPE
from time import strftime
from urllib2 import urlopen, URLError

# logging formatters
LOG_FORMATTER = "[%(asctime)s] %(name)s.%(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S %Z"

HTML_TEMPLATE = Template("""\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
    <head>
        <title>Version bump checker - {{ config_file }}</title>
        <meta http-equiv="content-type" content="text/html;charset=utf-8" />
    </head>
    <body>
        <h1>Version bump checker</h1>
        <h2>{{ config_file }}</h2>
        <table border="1">
            <tr>
                <th>Package</th>
                <th>Bugs</th>
                <th>Gentoo version</th>
                <th>Upstream version</th>
                <th>Up-to-date?</th>
            </tr>
            {%- for package in packages %}
            <tr>
                <td><a href="{{ package.url }}">{{ package.atom }}</a></td>
                <td><a href="http://bugs.gentoo.org/buglist.cgi?quicksearch={{ package.atom }}">Bugs</a></td>
                {%- if package.error %}
                <td colspan="3">Failed!</td>
                {%- else %}
                <td>{{ package.gentoo_version }}</td>
                <td>{{ package.upstream_version }}</td>
                <td bgcolor="{{ package.up2date and 'green">yes' or 'red">no' }}</td>
                {%- endif %}
            </tr>
            {%- else %}
            <tr>
                <td colspan="5">No packages available!</td>
            </tr>
            {%- endfor %}
        </table>
        <hr />
        <p>Last update: {{ last_update }}</p>
    </body>
</html>
""")

# setup logging
logger = getLogger('checkbump')
logger.setLevel(INFO)
_log_handler = StreamHandler(sys.stderr)
_log_handler.setFormatter(Formatter(LOG_FORMATTER, LOG_DATEFORMAT))
logger.addHandler(_log_handler)


class Package(object):
    
    error = False
    
    def __init__(self, atom, url):
        self.atom = atom
        self.url = url
        self.upstream_version = ''
        try:
            with closing(urlopen(url)) as fp:
                self._content = fp.read()
        except URLError, err:
            self.error = True
            logger.error('fetch failed %r - %r' % (atom, err.reason))
    
    @property
    def gentoo_version(self):
        if not self.error:
            portage = portagetree()
            versions = portage.dep_match(self.atom)
            if len(versions) == 0:
                raise Exception('package not found %r' % self.atom)
            last_atom = versions[-1]
            cp, pv, rev = pkgsplit(last_atom)
            return pv
    
    @property
    def up2date(self):
        if not self.error:
            return vercmp(self.gentoo_version, self.upstream_version) == 0
    
    def run_command(self, command):
        if not self.error:
            p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate(self._content)
            if p.returncode != os.EX_OK:
                raise Exception('command failed: %r' % command)
            self.upstream_version += stdout.strip()


class PackageList(list):
    
    def __init__(self, ini_file):
        self._parser = ConfigParser()
        parsed_file = self._parser.read(ini_file)
        if not len(parsed_file) == 1:
            raise Exception('failed to load config %r' % ini_file)
        list.__init__(self)
        atoms = self._parser.sections()
        atoms.sort()
        for atom in atoms:
            logger.info('fetching %r' % atom)
            url = None
            commands = None
            for name, value in self._parser.items(atom):
                if name == 'url':
                    url = value
                elif name == 'command':
                    commands = value
            if url is None or commands is None:
                raise Exception('invalid url/command %r' % atom)
            package = Package(atom, url)
            for command in commands.split('\n'):
                package.run_command(command.strip())
            self.append(package)


def generate_html(config_file, pkg_list):
    logger.info('generating html')
    return HTML_TEMPLATE.render(
        config_file = config_file,
        packages = pkg_list,
        last_update = strftime(LOG_DATEFORMAT)
    )


def main(argv):
    logger.info('starting ...')
    if len(argv) != 1:
        logger.error('invalid number of arguments.')
        return 1
    pkg_list = PackageList(argv[0])
    config_file = os.path.splitext(os.path.basename(argv[0]))[0]
    sys.stdout.write(generate_html(config_file, pkg_list))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        logger.info('interrupted.')
    except Exception, err:
        logger.error(str(err))
