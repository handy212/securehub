"""Console documentation browser at /console/help/."""

from django.views.generic import TemplateView

from apps.accounts.rbac import Perm

from .console_docs import get_help_page, help_nav_context, render_help_markdown
from .permissions import StaffRequiredMixin


class ConsoleHelpMixin(StaffRequiredMixin):
    required_console_permission = Perm.ACCESS
    template_name = "dashboard/help/page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug", "index")
        page = get_help_page(slug)
        if not page:
            from django.http import Http404

            raise Http404("Help page not found.")
        context.update(help_nav_context(slug))
        context["help_page"] = page
        context["help_html"] = render_help_markdown(page["file"])
        return context


class ConsoleHelpIndexView(ConsoleHelpMixin, TemplateView):
    def get_context_data(self, **kwargs):
        self.kwargs.setdefault("slug", "index")
        return super().get_context_data(**kwargs)


class ConsoleHelpPageView(ConsoleHelpMixin, TemplateView):
    pass
