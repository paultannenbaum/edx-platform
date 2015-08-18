"""
Call Stack Manager deals with tracking call stacks of functions/methods/classes(Django Model Classes)
Call Stack Manager logs unique call stacks. The call stacks then can be retrieved via Splunk, or log reads.

classes:
CallStackManager -  stores all stacks in global dictionary and logs
CallStackMixin - used for Model save(), and delete() method

Decorators:
@donottrack - Decorator that will halt tracking for parameterized entities,
 (or halt tracking anything in case of non-parametrized decorator).
@trackit - Decorator that will start tracking decorated entity.
@track_till_now - Will log every unique call stack of parametrized entity/ entities.

TRACKING DJANGO MODEL CLASSES -
Call stacks of Model Class
in three cases-
1. QuerySet API
2. save()
3. delete()

How to use:
1. Import following in the file where class to be tracked resides
    from openedx.core.djangoapps.call_stack_manager import CallStackManager, CallStackMixin
2. Override objects of default manager by writing following in any model class which you want to track-
    objects = CallStackManager()
3. For tracking Save and Delete events-
    Use mixin called "CallStackMixin"
    For ex.
        class StudentModule(models.Model, CallStackMixin):

TRACKING FUNCTIONS, and METHODS-
1. Import following-
    from openedx.core.djangoapps.call_stack_manager import trackit
NOTE - @trackit is non-parameterized decorator.

FOR DISABLING TRACKING-
1. Import following at appropriate location-
    from openedx.core.djangoapps.call_stack_manager import donottrack
** NOTE ** @donottrack accepts classes. However, while dealing with functions/methods, you should pass a string.
 The string has a specific format i.e. '<entity_name>.__module__ + "." + <entity_name>.__name__'

"""


import logging
import traceback
import re
import collections
import wrapt
import types
import inspect
from django.db.models import Manager

log = logging.getLogger(__name__)

# List of regular expressions acting as filters
REGULAR_EXPS = [re.compile(x) for x in ['^.*python2.7.*$', '^.*<exec_function>.*$', '^.*exec_code_object.*$',
                                        '^.*edxapp/src.*$', '^.*call_stack_manager.*$']]

# Flag which decides whether to track calls in the function or not. Default True.
TRACK_FLAG = True

# List keeping track of entities not to be tracked
HALT_TRACKING = []

#  Dictionary which stores call logs
# {'EntityName' : SetOf(ListOfFrames)}
# Frames - ('FilePath','LineNumber','Context')
#  {"<class 'courseware.models.StudentModule'>" : ([(file, line number, function name, context),(---,---,---)],
#                                                 [(file, line number, function name, context),(---,---,---)])}
STACK_BOOK = collections.defaultdict(list)


def capture_call_stack(entity_name):
    """ Logs customised call stacks in global dictionary STACK_BOOK and logs it.

    Arguments:
        entity_name - entity

    """
    # Holds temporary callstack
    # List with each element 4-tuple(filename, line number, function name, text)
    # and filtered with respect to regular expressions
    temp_call_stack = (frame for frame in [frames for frames in traceback.extract_stack()]
                       if not any(reg.match(frame[0]) for reg in REGULAR_EXPS))

    def _print(frame):
        """ Converts the tuple format of frame to a printable format

        Arguments:
            frame - current frame tuple of format (file, line number, function name, context)

        Returns:
            frame converted to a string in following format
            File XXX, line number XXX, in XXX
                XXXXX
        """
        return str('\n File ' + str(frame[0]) + ', line number ' + str(frame[1]) + ', in ' +
                   str(frame[2]) + '\n\t' + str(frame[3]))

    # Customize output of call stack
    final_call_stack = ""
    for frame in temp_call_stack:
        final_call_stack += _print(frame)

    def _should_get_logged(entity_name):
        """ checks if current call stack of current entity should be logged or not

        Arguments:
            entity_name - Name of the current entity

        Returns:
            True if the current call stack is to logged, False otherwise
        """
        if not HALT_TRACKING:
            if TRACK_FLAG and temp_call_stack not in STACK_BOOK[entity_name]:  # TRACK_FLAG False iff @donottrack
                return True
            else:
                return False
        else:
            if inspect.isclass(entity_name):
                if temp_call_stack not in STACK_BOOK[entity_name] and \
                        not issubclass(entity_name, tuple(HALT_TRACKING[-1])):
                    return True
                else:
                    return False
            else:  # Assumption : Everything other than "class" will be passed as string
                if temp_call_stack not in STACK_BOOK[entity_name] and entity_name not in tuple(HALT_TRACKING[-1]):
                    return True
                else:
                    return False

    if _should_get_logged(entity_name):
        STACK_BOOK[entity_name].append(temp_call_stack)
        log.info("Logging new call stack number %s for %s:\n %s", len(STACK_BOOK[entity_name]),
                 entity_name, final_call_stack)


class CallStackMixin(object):
    """ Mixin class for getting call stacks when save() and delete() methods are called
    """

    def save(self, *args, **kwargs):
        """ Logs before save() and overrides respective model API save()
        """
        capture_call_stack(type(self))
        return super(CallStackMixin, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """ Logs before delete() and overrides respective model API delete()
        """
        capture_call_stack(type(self))
        return super(CallStackMixin, self).delete(*args, **kwargs)


class CallStackManager(Manager):
    """ Manager class which overrides the default Manager class for getting call stacks
    """
    def get_query_set(self):
        """ Override the default queryset API method
        """
        if hasattr(self, 'model'):
            capture_call_stack(self.model)
        else:
            capture_call_stack(type(self))
        return super(CallStackManager, self).get_query_set()


def donottrack(*entities_not_to_be_tracked):
    """ Decorator which halts tracking for some entities for specific functions

    Arguments:
        entities_not_to_be_tracked: entities which are not to be tracked

    Returns:
        wrapped function
    """
    @wrapt.decorator
    def real_donottrack(wrapped, instance, args, kwargs):  # pylint: disable=W0613
        """ Takes function to be decorated and returns wrapped function

        Arguments:
            wrapped - The wrapped function which in turns needs to be called by wrapper function.
            instance - The object to which the wrapped function was bound when it was called.
            args - The list of positional arguments supplied when the decorated function was called.
            kwargs - The dictionary of keyword arguments supplied when the decorated function was called.

        Returns:
            return of wrapped function
        """
        if entities_not_to_be_tracked:
            global HALT_TRACKING  # pylint: disable=W0603
            HALT_TRACKING.append(entities_not_to_be_tracked)
            HALT_TRACKING[-1] = list(set([x for sublist in HALT_TRACKING for x in sublist]))
            return_value = wrapped(*args, **kwargs)

            # check if the returning class is a generator
            if isinstance(return_value, types.GeneratorType):
                def generator_wrapper(wrapped_generator):
                    try:
                        while True:
                            return_value = next(wrapped_generator)
                            yield return_value
                    finally:
                        HALT_TRACKING.pop()
                return generator_wrapper(return_value)
            else:
                HALT_TRACKING.pop()
                return return_value

        else:  # if donottrack is not parameterized
            global TRACK_FLAG  # pylint: disable=W0603
            TRACK_FLAG = False
            return_value = wrapped(*args, **kwargs)

            # check if the returning class is a generator
            if isinstance(return_value, types.GeneratorType):
                def generator_wrapper(wrapped_generator):
                    try:
                        while True:
                            return_value = next(wrapped_generator)
                            yield return_value
                    finally:
                        TRACK_FLAG = True
                return generator_wrapper(return_value)
            else:
                TRACK_FLAG = False
                return return_value
    return real_donottrack


@wrapt.decorator()
def trackit(wrapped, instance, args, kwargs):  # pylint: disable=W0613
    """ Decorator which tracks logs call stacks

    Arguments:
        wrapped - The wrapped function which in turns needs to be called by wrapper function.
        instance - The object to which the wrapped function was bound when it was called.
        args - The list of positional arguments supplied when the decorated function was called.
        kwargs - The dictionary of keyword arguments supplied when the decorated function was called.

    Returns:
        wrapped function
    """
    capture_call_stack(wrapped.__module__ + "." + wrapped.__name__)
    return wrapped(*args, **kwargs)
