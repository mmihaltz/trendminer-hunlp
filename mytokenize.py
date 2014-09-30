#!/usr/bin/python3
# coding: UTF-8

"""
Tokenize UTF-8 plain-text file (with #START lines) by calling Huntoken wrapper shellscript with customizations:
- identify URLs and keep them as single tokens
- fix huntoken output bug: <\n/s\n>\n => \n (exploded </s> EOS tag)
- insert missing spaces after punctuation between words (correct input text): eg. foo.Bar => foo. Bar
- remove period from end of a token if next token is "...", e.g. "alma...." tokenized as "alma.\n...\n" => "alma\n...\n"
  (Note: this will break correct(?) uses of abbreviations followed by ellipses e.g. "stb....")

Usage:
tokenize INFILE OUTFILE
 

"""

import os
import re
import sys
from pytimeout import Timeout


HUNTDIR = '/home/mihaltz/hun-tools'


GRUBER_URLINTEXT_PAT = re.compile(r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')
# from https://gist.github.com/uogbuji/705383

MISSING_SPACE_PAT = re.compile(r'([aábcdeéfghiíjklmnoóöőpqrstuúüűvwxyzAÁBCDEÉFGHIÍJKLMNOÓÖŐPQRSTUÚÜŰVWXYZ])([\.,]+)([aábcdeéfghiíjklmnoóöőpqrstuúüűvwxyzAÁBCDEÉFGHIÍJKLMNOÓÖŐPQRSTUÚÜŰVWXYZ])')
# no space after an interword punctuation

# global temp vars
URLS = []
UCNT = 0


def call_huntoken(inp, outp):
  """Calls huntokn command-line tokenizer via a system call.
     inp is untokenized string
     outp is the stream to write to.
  """
  import subprocess
  p = subprocess.Popen(HUNTDIR + '/010.huntoken', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  (stout, sterr) = p.communicate( bytes(tok_preproc(inp), encoding='UTF-8'))
  if p.returncode != 0:
    sys.stderr.write('Command returned with exitcode {0}'.format(p.returncode))
  else:
    outp.write( tok_postproc( str(stout, encoding='utf8')))

def _repl_url1(m):
  global URLS
  URLS.append(m.group(0))
  return '###URL###'

def _repl_url2(m):
  global URLS, UCNT
  UCNT += 1
  return URLS[UCNT-1]

def tok_preproc(inp):
  """Pre-processing before tokenization. inp is untokenized string (UTF-8).
  - identify URLS, save them, replace them with '###URL###' (to avoid tokenizer breaking up URLs)
  - insert missing spaces after punctuation between words (correct input text): eg. foo.Bar => foo. Bar
  """
  global URLS
  URLS = []
  # - identify URLS, save them, replace them with '###URL###' (to avoid tokenizer breaking up URLs)
  try:
    with Timeout(5):
      outp = GRUBER_URLINTEXT_PAT.sub(_repl_url1, inp)
  except Timeout.Timeout:
    sys.stderr.write('Warning (tokenize.py): URL regexp substitute timed out on line:\n{0}\n'.format(inp))
    outp = inp
  # - insert missing spaces after punctuation between words (correct input text): eg. foo.Bar => foo. Bar
  outp = MISSING_SPACE_PAT.sub(r'\1\2 \3', outp)
  return outp
    
def tok_postproc(inp):
  """Post-processing after tokenization. inp is tokenized string ('\n' for new token, '\n\n' for new sentence)
  - replace '###URL###' strings to original URL strings in message
  - fix huntoken output bug: <\n/s\n>\n => \n\n (exploded </s> EOS tag)
  - remove period from end of a token if next token is "...", e.g. "alma...." tokenized as "alma.\n...\n" => "alma\n...\n"
    (Note: this will break correct uses of abbreviations before ellipses. e.g. "stb....")
  """
  global UCNT
  UCNT = 0
  outp = re.sub(r'#\n#\n#\nURL\n#\n#\n#', _repl_url2, inp)
  outp = re.sub(r'<\n/s\n>\n', r'\n', outp)
  outp = re.sub(r'(\w+)\.\n\.\.\.\n', r'\1\n...\n', outp)
  return outp


if __name__ == '__main__':

  if len(sys.argv) != 3:
    sys.exit('Usage: mytokenize.py <input_filename> <output_filename>\n')
    
  inp = open(sys.argv[1])
  outp = open(sys.argv[2], 'w')
  
  for line in inp:
    line = line.rstrip()
    if line.startswith('#START_'):
      outp.write(line + '\n\n')
    else:
      #print('>>{0}<<'.format(line))
      call_huntoken(line, outp)

  inp.close()
  outp.close()
