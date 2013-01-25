from localtv.decorators import require_site_admin

from uploadtemplate import views

index = require_site_admin(views.ThemeIndexView.as_view())
update = require_site_admin(views.ThemeUpdateView.as_view())
create = require_site_admin(views.ThemeCreateView.as_view())
delete = require_site_admin(views.delete)
download = views.download
unset_default = require_site_admin(views.unset_default)
set_default = require_site_admin(views.set_default)
