#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Parser for tr-069-style data model .xml files."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import os.path
import re
import string
import sys
import xml.etree.ElementTree

import google3
import bup.options


optspec = """
parse-schema.py [-d dir] files...
--
d,output-dir= Directory to write files to
"""

DEFAULT_BASE_CLASS = 'core.Exporter'

chunks = {}
imports = {}


def Log(s):
  sys.stdout.flush()
  sys.stderr.write('%s\n' % s)


def AddChunk(spec, objtype, name, root):
  key = (spec, objtype, name)
  assert not chunks.has_key(key)
  chunks[key] = root


def FixSpec(spec):
  # When a spec refers to tr-xxx-1-0-0 or tr-xxx-1-0, we might have to
  # substitute in tr-xxx-1-0-1 instead (a bugfix revision).  Let's just
  # drop out the third version digit so it's easier to use as a dictionary
  # key.
  return re.sub(r':(tr|wt)-(\d+-\d+-\d+)-\d+$', r':tr-\2', spec)


def NiceSpec(spec):
  spec = re.sub(r'^urn:broadband-forum-org:', '', spec)
  spec = re.sub(r'^urn:google-com:', '', spec)
  spec = re.sub(r'^urn:catawampus-org:', '', spec)
  return spec


def SpecNameForPython(spec):
  spec = NiceSpec(spec)
  spec = re.sub(r'tr-(\d+)-(\d+)-(\d+)', r'tr\1_v\2_\3', spec)
  spec = spec.translate(string.maketrans('-', '_'))
  return spec


def ObjNameForPython(name):
  name = re.sub(r':(\d+)\.(\d+)', r'_v\1_\2', name)
  name = name.replace('-', '_')  # X_EXAMPLE-COM_foo vendor data models
  return name


def Indented(prefix, s):
  s = unicode(s)
  s = re.sub(re.compile(r'^', re.M), prefix, s)
  s = re.sub(re.compile(r'^\s+$', re.M), '', s)
  return s


IMPORT_BUG_FIXES = {
    # bugs in tr-181-2-0-1.  It tries to import *_Device2, which doesn't
    # seem to exist anywhere.
    ('urn:broadband-forum-org:tr-143-1-0', 'component',
     'DownloadDiagnostics_Device2'):
        ('urn:broadband-forum-org:tr-143-1-0', 'component',
         'DownloadDiagnostics'),
    ('urn:broadband-forum-org:tr-143-1-0', 'component',
     'UploadDiagnostics_Device2'):
        ('urn:broadband-forum-org:tr-143-1-0', 'component',
         'UploadDiagnostics'),
}


def ParseImports(into_spec, root):
  from_spec = FixSpec(root.attrib['spec'])
  for node in root:
    if node.tag in ('component', 'model'):
      from_name = node.attrib.get('ref', node.attrib['name'])
      into_name = node.attrib['name']
      from_key = (from_spec, node.tag, from_name)
      into_key = (into_spec, node.tag, into_name)
      if from_key in IMPORT_BUG_FIXES:
        from_key = IMPORT_BUG_FIXES[from_key]
      assert not chunks.has_key(into_key)
      assert not imports.has_key(into_key)
      imports[into_key] = from_key
    elif node.tag == 'dataType':
      continue
    else:
      raise KeyError(node.tag)


def ParseFile(filename):
  Log(filename)
  root = xml.etree.ElementTree.parse(open(filename)).getroot()
  spec = FixSpec(root.attrib['spec'])
  Log(NiceSpec(spec))
  for node in root:
    if node.tag == 'import':
      ParseImports(spec, node)
    elif node.tag in ('component', 'model'):
      name = node.attrib['name']
      Log('%-12s %-9s %s' % (NiceSpec(spec), node.tag, name))
      AddChunk(spec, node.tag, name, (spec, name, node))
    elif node.tag in ('description', 'dataType', 'bibliography'):
      continue
    else:
      Log('skip %s' % node.tag)


def ResolveImports():
  for k, v in sorted(imports.items()):
    prefix = ' %-12s %-9s %-20s ' % (NiceSpec(k[0]), k[1], k[2])
    Log('%s\n=%-12s %-9s %s' % (prefix, NiceSpec(v[0]), v[1], v[2]))
    while v in imports:
      v = imports[v]
      Log('=%-12s %-9s %s' % (NiceSpec(v[0]), v[1], v[2]))
    (into_spec, objtype, into_name) = k
    (from_spec, objtype, from_name) = v
    if objtype in ('component', 'model'):
      AddChunk(into_spec, objtype, into_name,
               chunks[(from_spec, objtype, from_name)])
    else:
      raise KeyError(objtype)


class Object(object):
  """Represents an <object> tag."""

  def __init__(self, model, name, prefix):
    self.model = model
    self.name = re.sub(r'-{i}', '', name)
    self.is_sequence = (self.name != name)
    self.prefix = prefix
    self.params = []
    self.object_sequence = []

  def __str__(self):
    pre = []
    out = []
    parent_class_name = DEFAULT_BASE_CLASS
    if self.model.parent_model_name:
      parent_class = self.FindParentClass()
      if parent_class:
        parent_class_name = '%s.%s' % (self.model.parent_model_name,
                                       parent_class.FullName())
    if parent_class_name.endswith('.'):
      # Only happens for toplevel Model objects
      parent_class_name = parent_class_name[:-1]
    fullname_with_seq = re.sub(r'-{i}', '.{i}', '.'.join(self.prefix[:-1]))
    classname = self.name.translate(string.maketrans('-', '_'))
    pre.append('class %s(%s):' % (classname, parent_class_name))
    classpath = '%s.%s' % (self.model.name, fullname_with_seq)
    if classpath.endswith('.'):
      classpath = classpath[:-1]
    pre.append('  """Represents %s."""' % classpath)
    if self.params or self.object_sequence:
      pre.append('')
      pre.append('  def __init__(self, **defaults):')
      pre.append('    %s.__init__(self, defaults=defaults)'
                 % parent_class_name)
      bits = []
      space = ',\n                '
      if self.params:
        quoted_param_list = ["'%s'" % param for param in self.params]
        quoted_params = (space+'        ').join(quoted_param_list)
        bits.append('params=[%s]' % quoted_params)
      obj_list = [obj.name for obj in self.object_sequence
                  if not obj.is_sequence]
      if obj_list:
        quoted_obj_list = ["'%s'" % obj for obj in obj_list]
        quoted_objs = (space+'         ').join(quoted_obj_list)
        bits.append('objects=[%s]' % quoted_objs)
      objlist_list = [obj.name for obj in self.object_sequence
                      if obj.is_sequence]
      if objlist_list:
        quoted_objlist_list = ["'%s'" % obj for obj in objlist_list]
        quoted_objlists = (space+'       ').join(quoted_objlist_list)
        bits.append('lists=[%s]' % quoted_objlists)
      pre.append('    self.Export(%s)' % (space.join(bits)))
    for obj in self.object_sequence:
      out.append('')
      out.append(Indented('  ', obj))
    if not self.params and not out:
      out.append('  pass')
    return '\n'.join(pre + out)

  def FindParentClass(self):
    parent_model = models.get((self.model.spec.name,
                               self.model.parent_model_name), None)
    while parent_model:
      parent_class = parent_model.objects.get(self.prefix, None)
      if parent_class:
        return parent_class
      parent_model = models.get((parent_model.spec.name,
                                 parent_model.parent_model_name), None)
    return None

  def FullName(self):
    return re.sub(r'-{i}', '', '.'.join(self.prefix[:-1]))


models = {}


class Model(object):
  """Represents a <model> tag."""

  def __init__(self, spec, name, parent_model_name):
    self.spec = spec
    self.name = ObjNameForPython(name)
    if parent_model_name:
      self.parent_model_name = ObjNameForPython(parent_model_name)
    else:
      self.parent_model_name = None
    self.items = {}
    self.objects = {}
    self.object_sequence = []
    models[(self.spec.name, self.name)] = self

  def _AddItem(self, parts):
    self.items[parts] = 1
    if not parts[-1]:
      if len(parts) > 2:
        self._AddItem(parts[:-2] + ('',))
    else:
      if len(parts) > 1:
        self._AddItem(parts[:-1] + ('',))

  def AddItem(self, name):
    parts = tuple(re.sub(r'\.{i}', r'-{i}', name).split('.'))
    self._AddItem(parts)

  def ItemsMatchingPrefix(self, prefix):
    assert (not prefix) or (not prefix[-1])
    for i in sorted(self.items):
      if i[:len(prefix)-1] == prefix[:-1] and i != prefix:
        yield i[len(prefix)-1:]

  def Objectify(self, name, prefix):
    """Using self.items, fill self.objects and self.object_sequence.

    Args:
      name: the basename of this object in the hierarchy.
      prefix: a list of parent object names.
    Returns:
      The toplevel Object generated, which corresponds to the Model itself.
    """
    assert (not prefix) or (not prefix[-1])
    obj = Object(self, name, prefix)
    self.objects[prefix] = obj
    for i in self.ItemsMatchingPrefix(prefix):
      if len(i) == 1 and i[0]:
        # a parameter of this object
        obj.params.append(i[0])
      elif len(i) == 2 and not i[1]:
        # a sub-object of this object
        subobj = self.Objectify(i[0], prefix[:-1] + i)
        obj.object_sequence.append(subobj)
    return obj

  def MakeObjects(self):
    assert not self.object_sequence
    obj = self.Objectify(self.name, ('',))
    self.object_sequence = [obj]

  def __str__(self):
    out = []
    for obj in self.object_sequence:
      out.append(Indented('', obj))
      out.append('')
    return '\n'.join(out)


def RenderParameter(model, prefix, xmlelement):
  name = xmlelement.attrib.get('base', xmlelement.attrib.get('name', '<??>'))
  model.AddItem('%s%s' % (prefix, name))


def RenderObject(model, prefix, spec, xmlelement):
  name = xmlelement.attrib.get('base', xmlelement.attrib.get('name', '<??>'))
  prefix += name
  model.AddItem(prefix)
  for i in xmlelement:
    if i.tag == 'parameter':
      RenderParameter(model, prefix, i)
    elif i.tag == 'object':
      RenderObject(model, prefix, spec, i)
    elif i.tag in ('description', 'uniqueKey'):
      pass
    else:
      raise KeyError(i.tag)


def RenderComponent(model, prefix, spec, xmlelement):
  for i in xmlelement:
    if i.tag == 'parameter':
      RenderParameter(model, prefix, i)
    elif i.tag == 'object':
      RenderObject(model, prefix, spec, i)
    elif i.tag == 'component':
      #pylint: disable-msg=W0612
      refspec, refname, ref = chunks[spec, 'component', i.attrib['ref']]
      refpath = ref.attrib.get('path', ref.attrib.get('name', '<?>'))
      RenderComponent(model, prefix, refspec, ref)
    elif i.tag in ('profile', 'description'):
      pass
    else:
      raise KeyError(i.tag)


specs = {}


class Spec(object):
  """Represents a <spec> tag."""

  def __init__(self, name):
    self.name = SpecNameForPython(name)
    self.aliases = []
    self.models = []
    self.deps = []
    specs[name] = self

  def __str__(self):
    out = []
    implist = []
    for (fromspec, fromname), (tospec, toname) in self.aliases:
      fromname = ObjNameForPython(fromname)
      tospec = SpecNameForPython(tospec)
      toname = ObjNameForPython(toname)
      if (fromspec, fromname) not in models:
        models[(fromspec, fromname)] = models[(tospec, toname)]
        Log('aliased %r' % ((fromspec, fromname),))
      if toname != fromname:
        implist.append((tospec,
                        'from %s import %s as %s'
                        % (tospec, toname, fromname)))
      else:
        implist.append((tospec,
                        'from %s import %s'
                        % (tospec, toname)))
    for imp in sorted(implist):
      out.append(imp[1])
    out.append('')
    out.append('')
    for model in self.models:
      out.append(str(model))
      out.append('')

    if self.models:
      out.append("if __name__ == '__main__':")
      for model in self.models:
        out.append('  print core.DumpSchema(%s)' % model.name)
    return '\n'.join(out) + '\n'

  def MakeObjects(self):
    for (fromspec, fromname), (tospec, toname) in self.aliases:
      fromname = ObjNameForPython(fromname)
      tospec = SpecNameForPython(tospec)
      toname = ObjNameForPython(toname)
      if (fromspec, fromname) not in models:
        models[(fromspec, fromname)] = models[(tospec, toname)]
        Log('aliased %r' % ((fromspec, fromname),))


def main():
  o = bup.options.Options(optspec)
  (opt, unused_flags, extra) = o.parse(sys.argv[1:])

  output_dir = opt.output_dir or '.'
  Log('Output directory for generated files is %s' % output_dir)

  for filename in extra:
    ParseFile(filename)
  ResolveImports()
  Log('Finished parsing and importing.')

  items = sorted(chunks.items())
  for (specname, objtype, name), (refspec, refname, xmlelement) in items:
    spec = specs.get(specname, None) or Spec(specname)
    if objtype == 'model':
      objname = ObjNameForPython(name)
      parent = xmlelement.attrib.get('base', None)
      if SpecNameForPython(refspec) != spec.name:
        spec.deps.append(refspec)
        spec.aliases.append(((spec.name, objname),
                             (refspec, refname)))
      else:
        if parent:
          model = Model(spec, objname, parent_model_name=parent)
        else:
          model = Model(spec, objname, parent_model_name=None)
        RenderComponent(model, '', refspec, xmlelement)
        model.MakeObjects()
        spec.models.append(model)

  Log('Finished models.')

  for spec in specs.values():
    spec.MakeObjects()
  for specname, spec in sorted(specs.items()):
    pyspec = SpecNameForPython(specname)
    assert pyspec.startswith('tr') or pyspec.startswith('x_')
    outf = open(os.path.join(output_dir, '%s.py' % pyspec), 'w')
    outf.write('#!/usr/bin/python\n'
               '# Copyright 2011 Google Inc. All Rights Reserved.\n'
               '#\n'
               '# AUTO-GENERATED BY parse-schema.py\n'
               '#\n'
               '# DO NOT EDIT!!\n'
               '#\n'
               '#pylint: disable-msg=C6202\n'
               '#pylint: disable-msg=C6409\n'
               '#pylint: disable-msg=C6310\n'
               '# These should not actually be necessary (bugs in gpylint?):\n'
               '#pylint: disable-msg=E1101\n'
               '#pylint: disable-msg=W0231\n'
               '#\n'
               '"""Auto-generated from spec: %s."""\n'
               '\n'
               'import core\n'
               % specname)
    outf.write(str(spec))


if __name__ == '__main__':
  main()
