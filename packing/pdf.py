from django.views.generic import View
from django.template.loader import get_template
from django.http import HttpResponse
from weasyprint import HTML

class MyPDFView(View):
    template_name = 'my_template.html'  # ton template Django

    def get_context_data(self):
        # Retourne le contexte que tu passes au template
        return {
            'data': 'Voici des données à afficher dans le PDF',
            # ajoute d'autres clés selon ton template
        }

    def get(self, request, *args, **kwargs):
        template = get_template(self.template_name)
        html_string = template.render(self.get_context_data())

        # Générer le PDF
        pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

        # Créer la réponse HTTP avec le bon type et headers pour téléchargement
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="mon_document.pdf"'

        return response
