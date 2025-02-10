from django.shortcuts import render
from django.http import JsonResponse
from waterdemands.models import PopulationData, PopulationDataYear, FloatingData

def main_page(request):
    """Render the main sewage estimation page."""
    return render(request, 'sewage/main.html')

def get_locations(request):
    """Fetch hierarchical location data."""
    state_code = request.GET.get("state_code")
    district_code = request.GET.get("district_code")
    subdistrict_code = request.GET.get("subdistrict_code")
    village_code = request.GET.get("village_code")

    if not state_code:
        # Fetch all unique states
        locations = PopulationData.objects.filter(district_code=0, subdistrict_code=0, village_code=0)
        location_list = [{"code": loc.state_code, "name": loc.region_name} for loc in locations]
        return JsonResponse(location_list, safe=False)

    elif state_code and not district_code:
        # Fetch districts within the given state
        locations = PopulationData.objects.filter(state_code=state_code, subdistrict_code=0, village_code=0)
        location_list = [
            {"code": loc.district_code, "name": " ALL" if loc.district_code == 0 else loc.region_name} 
            for loc in locations
        ]
        return JsonResponse(location_list, safe=False)

    elif state_code and district_code and not subdistrict_code:
        # Fetch subdistricts within the given state and district
        locations = PopulationData.objects.filter(state_code=state_code, district_code=district_code, village_code=0)
        location_list = [
            {"code": loc.subdistrict_code, "name": " ALL" if loc.subdistrict_code == 0 else loc.region_name} 
            for loc in locations
        ]
        return JsonResponse(location_list, safe=False)

    elif state_code and district_code and subdistrict_code:
        # Fetch villages within the given state, district, and subdistrict
        locations = PopulationData.objects.filter(
            state_code=state_code, district_code=district_code, subdistrict_code=subdistrict_code
        )
        location_list = [{"code": loc.village_code, "name": loc.region_name} for loc in locations]
        return JsonResponse(location_list, safe=False)

    elif state_code and district_code and subdistrict_code and village_code:
        # Fetch the population of the selected village for 2011
        try:
            village_population_2011 = PopulationData.objects.filter(
                state_code=state_code,
                district_code=district_code,
                subdistrict_code=subdistrict_code,
                village_code=village_code
            ).values_list('population_2011', flat=True).first()
            print("village_population_2011:", village_population_2011)
            if village_population_2011 is None:
                return JsonResponse({"error": "Population data not found for the selected village."}, status=404)

            return JsonResponse({"village_population_2011": village_population_2011}, safe=False)
        

        except PopulationData.DoesNotExist:
            return JsonResponse({"error": "Village not found."}, status=404)
        

    # Invalid request
    return JsonResponse({"error": "Invalid parameters or hierarchy."}, status=400)




def get_floating(request):
    """Fetch floating population based on state, district, and enumeration type."""
    state_code = request.GET.get("state_code")
    district_code = request.GET.get("district_code")
    subdistrict_code = request.GET.get("subdistrict_code")
    villages = request.GET.getlist("villages[]")
    enu = request.GET.get("enu")  # Enumeration type: Total, Urban, Rural

    if not (state_code and district_code and enu and subdistrict_code and villages):
        return JsonResponse({"error": "Missing required parameters."}, status=400)

    try:
        # Query the floating population data
        floating_populations = FloatingData.objects.filter(
            state_code=state_code,
            district_code=district_code,
            enumeration_code=enu,
            subdistrict_code=subdistrict_code,
            village_code__in=villages
        ).values_list('floating_pop', flat=True)

        floating_population=sum(floating_populations)

        if floating_population is None:
            return JsonResponse({"error": "No floating population data found."}, status=404)

        # Return the floating population
        return JsonResponse({"floating_population": floating_population}, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_combined_population(request):
    """Fetch combined population for selected villages."""
    state_code = request.GET.get("state_code")
    district_code = request.GET.get("district_code")
    subdistrict_code = request.GET.get("subdistrict_code")
    year = request.GET.get("year")  # For domestic method
    villages = request.GET.getlist("villages[]")  # Get list of selected villages
    intermediate_stage = request.GET.get("intermediate_stage")  # For Firefighting

    if not (state_code and district_code and subdistrict_code and villages):
        return JsonResponse({"error": "Missing required parameters."}, status=400)

    try:
        # Fetch village population for 2011 for all selected villages
        village_populations_2011 = PopulationData.objects.filter(
            state_code=state_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code,
            village_code__in=villages
        ).values_list('population_2011', flat=True)

        combined_village_population_2011 = sum(village_populations_2011)

        # Fetch subdistrict population for 2011
        subdistrict_population_2011 = PopulationDataYear.objects.filter(
            state_code=state_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code
        ).values_list('population_2011', flat=True).first() or 0

        if subdistrict_population_2011 == 0:
            return JsonResponse({"error": "Subdistrict population is zero; cannot calculate proportion."}, status=400)

        # Calculate proportion `k` for combined population
        k = combined_village_population_2011 / subdistrict_population_2011

        # Fetch population data from PopulationDataYear
        population_data = PopulationDataYear.objects.filter(
            state_code=state_code,
            district_code=district_code,
            subdistrict_code=subdistrict_code
        ).first()

        if not population_data:
            return JsonResponse({"error": "Population data not found for the selected region."}, status=404)

        # Retrieve population values for each decade
        populations = [
            getattr(population_data, f"population_{yr}", 0) or 0
            for yr in range(1951, 2012, 10)
        ]

        # Calculate differences between decades
        differences = [populations[i] - populations[i - 1] for i in range(1, len(populations))]
        avgd = sum(differences) / len(differences) if differences else 0

        # Calculate differences of differences
        accelerations = [differences[i] - differences[i - 1] for i in range(1, len(differences))]
        mavg = sum(accelerations) / len(accelerations) if accelerations else 0

        if year:
            if year.isdigit() and int(year) > 2011:
                year_int = int(year)
                n = (year_int - 2011) / 10

                # Calculate the projected population using extrapolated growth
                combined_population = (
                    combined_village_population_2011 + k * n * avgd + k * (n * (n + 1) * mavg) / 2
                )
                return JsonResponse({
                    "combined_population": round(combined_population, 2)
                }, safe=False)

        # **Handle Firefighting Method**
        # **Handle Firefighting Method**
        if intermediate_stage:
            if intermediate_stage.isdigit() and 1 <= int(intermediate_stage) <= 30:
                intermediate_stage = int(intermediate_stage)
                year_intermediate = 2021 + intermediate_stage  # Calculate the year
                n = (year_intermediate - 2011) / 10

                # Calculate the projected population for the intermediate stage
                intermediate_population = (
                    combined_village_population_2011 + k * n * avgd + k * (n * (n + 1) * mavg) / 2
                )

                return JsonResponse({
                    "intermediate_stage_population": round(intermediate_population, 2)
                }, safe=False)
            else:
                return JsonResponse({"error": "Invalid intermediate stage selected."}, status=400)


    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)