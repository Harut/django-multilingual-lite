# -*- coding: utf-8 -*-
from django.db import models
from django_utils.middleware import get_request
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import curry
from django.db.models.base import ModelBase
import copy

def _get_lang():
    try:
        return get_request().LANGUAGE_CODE
    except:
        from django.conf import settings
        return settings.LANGUAGE_CODE

class PublishManager(models.Manager):
    """
        Includes only objects marked as publish on current
    """
    def get_query_set(self):
        name = _get_lang() + '_publish'
        return super(PublishManager, self).get_query_set().filter(**{str(name): True})

class MultilingualManager(models.Manager):
    """
        Translates multilingual filter kwargs
    """
    
    def _translate(self, **kwargs):
        if hasattr(self.model, 'trans_fields'):
            for key in kwargs.keys():
                if key in self.model.trans_fields:
                    kwargs[str(_get_lang() + '_' + key)] = kwargs.pop(key)
        return kwargs

    def filter(self, **kwargs):
        return super(MultilingualManager, self).filter(**self._translate(**kwargs))

    def exclude(self, **kwargs):
        return super(MultilingualManager, self).exclude(**self._translate(**kwargs))

    def create(self, **kwargs):
        from django.conf import settings
        langs = [x[0] for x in settings.LANGUAGES]
        lang = _get_lang()
        langs = dict((l, 1) for l in langs)

        if hasattr(self.model, 'trans_fields'):
            for key in kwargs.keys():
                if key in self.model.trans_fields:
                    val = kwargs.pop(key)
                    for l in langs:
                        if not langs.has_key(l + '_' + key):
                            kwargs[l + '_' + key] = val
        
        return super(MultilingualManager, self).create(**kwargs)


class MultilingualMetaclass(models.base.ModelBase):
    """
        Metaclass for multilingual models.
        Creates dublicated fields in database. See also MultilingualBase.
        For fields named publish initializes Publish manager
        
        Usage:
        
        class MultilingualModel(SomeModel):
            __metaclass__ = MultilingualBase
            trans_fields = ('title',)
            multilingual_languages = ('ru', 'en')
            
            title = models.CharField(...)
            
        
    """
    
    def __new__(cls, name, bases, attrs):
        languages = attrs.get('multilingual_languages', ('ru', 'en'))
        trans_fields = attrs.get('trans_fields', None)

        if trans_fields is not None:
            attrs['objects'] =   MultilingualManager()
            if 'publish' in trans_fields: 
                attrs['published'] = PublishManager()
        
        cls = super(MultilingualMetaclass, cls).__new__(cls, name, bases, attrs)
        
        def _add_field(lang, nm, field):
            field_lang = copy.copy(field)
            
            field_lang.attname = lang + '_' + field_lang.attname
            field_lang.name = lang + '_' + field_lang.name
            field_lang.column = lang + '_' + field_lang.column
            field_lang.verbose_name = unicode(field_lang.verbose_name) + ' ('+lang+')'
            cls.add_to_class(lang + '_' + nm, field_lang)
            
        if languages is not None and trans_fields is not None:
            require_published = False
            for nm in trans_fields:
                    
                for i, field in enumerate(cls._meta.local_fields):
                    if field.name == nm: break
                if field.name != nm: break
                
                del cls._meta.local_fields[i]
                for lang in languages:
                    _add_field(lang, nm, field)
                        
    
            _get_value = lambda s, n: getattr(s, _get_lang() + '_' + n)
            _set_value = lambda s, v, n: setattr(s, _get_lang() + '_' + n, v)
    
            for field in trans_fields:
                cls.add_to_class(field, property(curry(_get_value, n=field),
                        curry(_set_value, n=field) )
                )
        return cls
        


class MultilingualBase(models.Model):
    """
        Base class for multilingual models.

        class MultilingualModel(MultilingualBase):

            trans_fields = ('title',)
            multilingual_languages = ('ru', 'en')
            
            title = models.CharField(...)
    
    """
    
    __metaclass__ = MultilingualMetaclass

    class Meta:
        abstract = True
