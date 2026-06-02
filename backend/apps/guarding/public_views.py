"""Public guard applicant intake (no console login required)."""

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from .applicant_intake import applicant_form_choices, create_application_from_request
from .public_intake import PUBLIC_DOCUMENT_SLOTS


class PublicGuardApplyView(TemplateView):
    template_name = "guarding/public/apply.html"

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "GUARD_PUBLIC_APPLY_ENABLED", True):
            raise Http404("Public applications are not available.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(applicant_form_choices())
        context["document_slots"] = PUBLIC_DOCUMENT_SLOTS
        context["form_errors"] = self.request.session.pop("apply_form_errors", None)
        context["old_post"] = self.request.session.pop("apply_form_post", {})
        try:
            context["initial_step"] = max(1, min(4, int(self.request.session.pop("apply_form_step", 1))))
        except (TypeError, ValueError):
            context["initial_step"] = 1
        return context

    def post(self, request, *args, **kwargs):
        try:
            applicant = create_application_from_request(
                request,
                source="public_web",
                is_public=True,
            )
        except ValueError as exc:
            request.session["apply_form_errors"] = str(exc)
            request.session["apply_form_post"] = {
                key: request.POST.get(key, "")
                for key in request.POST
                if not key.startswith("document_file")
            }
            try:
                request.session["apply_form_step"] = max(
                    1, min(4, int(request.POST.get("_apply_step", 4)))
                )
            except (TypeError, ValueError):
                request.session["apply_form_step"] = 4
            messages.error(request, str(exc))
            return redirect(reverse("guarding-public-apply"))

        return redirect(reverse("guarding-public-apply-success", kwargs={"applicant_id": applicant.pk}))


class PublicGuardApplySuccessView(TemplateView):
    template_name = "guarding/public/apply_success.html"

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "GUARD_PUBLIC_APPLY_ENABLED", True):
            raise Http404("Public applications are not available.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from .models import GuardApplicant

        context = super().get_context_data(**kwargs)
        applicant = GuardApplicant.objects.filter(pk=kwargs["applicant_id"]).first()
        if not applicant or applicant.source != "public_web":
            raise Http404("Application not found.")
        context["applicant"] = applicant
        context["reference_id"] = str(applicant.pk)[:8].upper()
        return context
