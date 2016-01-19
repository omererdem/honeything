from __future__ import with_statement
from StringIO import StringIO
from xml.sax import saxutils
from keyword import kwlist as PYTHON_KWORD_LIST

__all__ = ['Builder', 'Element']
__license__ = 'BSD'
__version__ = '0.2.1'
__author__ = "Jonas Galvez <http://jonasgalvez.com.br/>"
__contributors__ = ["bbolli <http://github.com/bbolli/>",
                    "masklinn <http://github.com/masklinn/>"]

class Builder:
    
    def __init__(self, encoding='utf-8', indent=' '*2, version=None):
        self._document = StringIO()
        self._encoding = encoding
        self._indent = indent
        self._indentation = 0
        if version is not None:
            self.write('<?xml version="%s" encoding="%s"?>\n' % (
                version, encoding
            ))
    
    def __getattr__(self, name):
        return Element(name, self)
        
    def __getitem__(self, name):
        return Element(name, self)
    
    def __str__(self):
        return self._document.getvalue().encode(self._encoding).strip()
        
    def __unicode__(self):
        return self._document.getvalue().decode(self._encoding).strip()
        
    def write(self, content):
        """Write raw content to the document"""
        if type(content) is not unicode:
            content = content.decode(self._encoding)
        self._document.write('%s' % content)

    def write_escaped(self, content):
        """Write escaped content to the document"""
        self.write(saxutils.escape(content))
        
    def write_indented(self, content):
        """Write indented content to the document"""
        self.write('%s%s\n' % (self._indent * self._indentation, content))

builder = Builder # 0.1 backward compatibility

class Element:
    
    PYTHON_KWORD_MAP = dict([(k + '_', k) for k in PYTHON_KWORD_LIST])
    
    def __init__(self, name, builder):
        self.name = self._nameprep(name)
        self.builder = builder
        self.attributes = {}
        
    def __enter__(self):
        """Add a parent element to the document"""
        self.builder.write_indented('<%s%s>' % (
            self.name, self._serialized_attrs()
        ))
        self.builder._indentation += 1
        return self
        
    def __exit__(self, type, value, tb):
        """Add close tag to current parent element"""
        self.builder._indentation -= 1
        self.builder.write_indented('</%s>' % self.name)
        
    def __call__(*args, **kargs):
        """Add a child element to the document"""
        self = args[0]
        self.attributes.update(kargs)
        if len(args) > 1:
            value = args[1]
            if value is None:
                self.builder.write_indented('<%s%s />' % (
                    self.name, self._serialized_attrs()
                ))
            else:
                value = saxutils.escape(value)
                self.builder.write_indented('<%s%s>%s</%s>' % (
                    self.name, self._serialized_attrs(), value, self.name
                ))
        return self

    def _serialized_attrs(self):
        """Serialize attributes for element insertion"""
        serialized = []
        for attr, value in self.attributes.items():
            serialized.append(' %s=%s' % (
                self._nameprep(attr), saxutils.quoteattr(value)
            ))
        return ''.join(serialized)

    def _nameprep(self, name):
        """Undo keyword and colon mangling"""
        name = Element.PYTHON_KWORD_MAP.get(name, name)
        return name.replace('__', ':')
