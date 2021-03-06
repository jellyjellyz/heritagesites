from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.views import generic

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django_filters.views import FilterView


from .forms import HeritageSiteForm
from .models import HeritageSite, CountryArea, HeritageSiteJurisdiction
from .filters import HeritageSiteFilter

def index(request):
	return HttpResponse("Hello, world. You're at the UNESCO Heritage Sites index page.")

class LogoutPageView(generic.TemplateView):
	template_name = 'registration/logout.html'

class AboutPageView(generic.TemplateView):
	template_name = 'heritagesites/about.html'


class HomePageView(generic.TemplateView):
	template_name = 'heritagesites/home.html'

class SiteFilterView(FilterView):
	filterset_class = HeritageSiteFilter
	template_name = 'heritagesites/site_filter.html'

class SiteListView(generic.ListView):
	model = HeritageSite
	context_object_name = 'sites'
	template_name = 'heritagesites/site.html'
	paginate_by = 50

	def get_queryset(self):
		return HeritageSite.objects\
				.all()\
				.select_related('heritage_site_category')\
				.order_by('site_name')

class SiteDetailView(generic.DetailView):
	model = HeritageSite
	context_object_name = 'site'
	template_name = 'heritagesites/site_detail.html'
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		country_area_display = []
		region_display = []
		for ca in self.object.country_area.all():
			country_area_display.append(ca.country_area_name.strip())
			temp = []
			if ca.location.intermediate_region:
				temp.append(ca.location.intermediate_region.intermediate_region_name)
			elif ca.location.sub_region:
				temp.append(ca.location.sub_region.sub_region_name)
			elif ca.location.region:
				temp.append(ca.location.region.region_name)
			elif ca.location.planet:
				temp.append(ca.location.planet.unsd_name)
			temp = ' '.join(temp)
			if temp not in region_display:
				region_display.append(temp)

		context['country_area_display'] = ', '.join(country_area_display)
		context['region_display'] = ', '.join(region_display)
		# print(context)
		return context
	
@method_decorator(login_required, name='dispatch')
class SiteCreateView(generic.View):
	model = HeritageSite
	form_class = HeritageSiteForm
	success_message = "Heritage Site created successfully"
	template_name = 'heritagesites/site_new.html'
	# field = '__all__' <-- superseded by form_class
	# success_url = reverse_lazy('heritagesites/site_list')

	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def post(self, request):
		form = HeritageSiteForm(request.POST)
		if form.is_valid():
			site = form.save(commit=False)
			site.save()
			for country in form.cleaned_data['country_area']:
				HeritageSiteJurisdiction.objects.create(heritage_site=site, country_area=country)
			return redirect(site) # shortcut to object's get_absolute_url()
		return render(request, 'heritagesites/site_new.html', {'form': form})
	
	def get(self, request):
		form = HeritageSiteForm()
		return render(request, 'heritagesites/site_new.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class SiteUpdateView(generic.UpdateView):
	model = HeritageSite
	form_class = HeritageSiteForm
	context_object_name = 'site'
# 	# pk_url_kwarg = 'site_pk'
	success_message = "Heritage Site updated successfully"
	template_name = 'heritagesites/site_update.html'

	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		site = form.save(commit=False)
		# site.updated_by = self.request.user
		# site.date_updated = timezone.now()
		site.save()

		# Current country_area_id values linked to site
		old_ids = HeritageSiteJurisdiction.objects\
					.values_list('country_area_id', flat=True)\
					.filter(heritage_site_id=site.heritage_site_id)
		
		# New countries list
		new_countries = form.cleaned_data['country_area']

		# New ids
		new_ids = []

		# Insert new unmatched country entries
		for country in new_countries:
			new_id = country.country_area_id
			new_ids.append(new_id)
			if new_id in old_ids:
				continue
			else:
				HeritageSiteJurisdiction.objects\
				.create(heritage_site=site, country_area=country)

		# Delete old unmatched country entries
		for old_id in old_ids:
			if old_id in new_ids:
				continue
			else:
				HeritageSiteJurisdiction.objects\
				.filter(heritage_site_id=site.heritage_site_id, country_area_id=old_id)\
				.delete()

		return HttpResponseRedirect(site.get_absolute_url())


@method_decorator(login_required, name='dispatch')
class SiteDeleteView(generic.DeleteView):
	model = HeritageSite
	success_message = "Heritage Site deleted successfully"
	success_url = reverse_lazy('sites')
	context_object_name = 'site'
	template_name = 'heritagesites/site_delete.html'

	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def delete(self, request, *args, **kwargs):
		self.object = self.get_object()

		# Delete HeritageSiteJurisdiction entries
		HeritageSiteJurisdiction.objects \
			.filter(heritage_site_id=self.object.heritage_site_id) \
			.delete()

		self.object.delete()

		return HttpResponseRedirect(self.get_success_url())


@method_decorator(login_required, name='dispatch')
class CountryAreaListView(generic.ListView):
	model = CountryArea
	context_object_name = 'countries'
	template_name = 'heritagesites/country_area.html'
	paginate_by = 20

	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get_queryset(self):
		return CountryArea.objects\
				.all()\
				.select_related('location', 'dev_status')\
				.order_by('country_area_name')

@method_decorator(login_required, name='dispatch')
class CountryAreaDetailView(generic.DetailView):
	model = CountryArea
	context_object_name = 'country'
	template_name = 'heritagesites/country_area_detail.html'

	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)
