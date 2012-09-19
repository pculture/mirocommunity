from django import template
register = template.Library()

### Based on http://djangosnippets.org/snippets/1243/
def do_generate_modified_query_string(parser, token):
   try:
       tag_name, key, value = token.split_contents()
   except ValueError:
       return GetStringNode()

   if not (key[0] == key[-1] and key[0] in ('"', "'")):
       raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name

   return GetStringNode(key[1:-1], value)

class GetStringNode(template.Node):
   def __init__(self, key=None, value=None):
       self.key = key
       if value:
           self.value = template.Variable(value)

   def render(self, context):
       get = context.get('request').GET.copy()

       if self.key:
           actual_value = self.value.resolve(context)
           get.__setitem__(self.key, actual_value)

       return get.urlencode()

register.tag('generate_modified_query_string', do_generate_modified_query_string)


