"""Signals related to the comments service."""

from django.dispatch import Signal


thread_created = Signal(providing_args=['user'])
thread_edited = Signal(providing_args=['user'])
thread_voted = Signal(providing_args=['user'])
comment_created = Signal(providing_args=['user'])
comment_edited = Signal(providing_args=['user'])
comment_voted = Signal(providing_args=['user'])
comment_endorsed = Signal(providing_args=['user'])
