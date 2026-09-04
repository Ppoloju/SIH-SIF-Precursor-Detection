"""Generate a realistic, balanced 500-report dataset for SIF model evaluation.

Dataset balance:
- Total records: 500
- SIF-potential (Yes): 150 (30%)
- Non-SIF (No): 350 (70%)
"""

import os
import pandas as pd

SIF_POSITIVE_TEMPLATES = [
    "During maintenance, technician started work on a live pipeline without properly isolating the energy source LOTO tag missing.",
    "Worker began servicing the pump while it was still energized; LOTO isolation tag was missing.",
    "A contractor bypassed the lockout tagout on the compressor to save time and started the maintenance job.",
    "Operator opened the high pressure gas line without depressurizing it; fitting blew off creating severe line of fire hazard.",
    "Near-miss: flange coupling slipped while the line was still pressurized during line opening.",
    "Two workers entered the hydrocarbon storage tank without gas testing PTW and no standby attendant was posted.",
    "Crew entered the confined space vessel without checking oxygen and H2S levels; rescue tripod equipment not installed.",
    "Contractor ne bina gas test ke tank ke andar kaam shuru kar diya aur koi attendant nahi tha.",
    "Roof worker was seen working at height of 8 meters without a safety harness; scaffold lacked top guardrails.",
    "Technician climbed damaged extension ladder to repair light fixture at height without any harness or ladder securing.",
    "Barricading was removed around open excavation pit; worker walked within 0.5m of unprotected edge.",
    "Near-miss: falling spanner dropped from scaffold 4th lift landing area; barricade missing below.",
    "Welding was carried out near fuel storage tank without a hot work permit PTW and no fire watch posted.",
    "Gas cylinder left unsecured next to active welding station without safety chain or flash back arrestor.",
    "Oily rags and flammable solvent drums were left directly next to welding grinding station sparks.",
    "The crane operator lowered 5-ton pipe bundle onto truck without a banksman spotter guiding the swing.",
    "Worker stood directly under suspended drill pipe load while the crane was lifting.",
    "Rigging sling showed severed wire strands but was used for heavy manifold lift without inspection.",
    "Driver exceeded yard speed limit in heavy vehicle loaded with diesel fuel and bypassed pre-drive safety check.",
    "Employees stood directly in blind spot path of reversing fuel tanker in loading bay without spotter.",
    "Operator entered sour gas well pad without personal H2S gas detector; stationary gas monitor was out of service.",
    "H2S gas alarm sounded at compressor station but crew continued working without wearing emergency BA sets.",
    "Mechanic removed machine safety guard and defeated interlock switch to clear jam while conveyor was running.",
    "Emergency stop button on main discharge pump was blocked by heavy timber and could not be actuated.",
    "Excavation deeper than 1.5 meters started without work authorization permit PTW and no trench shoring installed.",
    "Technician replaced light bulb on live 415V electrical switchgear circuit without using insulated tools or PPE.",
    "Electrician touched open terminal box while circuit breaker was still energized and not tagged out.",
    "Kaam shuru karne se pehle gas detector nahi pehna tha aur area mein H2S gas ka khatra tha.",
    "Technician ne pipeline par kaam shuru kiya bina isolation ke, line pressurize thi LOTO nahi tha.",
    "Crane operator banksman chara load uthalo, niche worker kaam korte chilo.",
    "হারনেস ছাড়া উঁচু ছাদে কাজ চলছিল, কোনো ফল প্রোটেকশন ছিল না।",
    "ট্যাংকিত সোমোৱাৰ আগত গেছ টেষ্ট নকৰাকৈ কাম আৰম্ভ হৈছিল আৰু এটেণ্ডেণ্ট নাছিল।",
]

NON_SIF_TEMPLATES = [
    "The crew isolated and depressurized the pipeline before maintenance began; LOTO tags applied and verified.",
    "All workers wore safety harnesses with proper anchorage; gas tests done before tank entry and oxygen was 20.9%.",
    "Confined space entry was performed with valid PTW permit, calibrated gas monitor and standby man posted.",
    "Fall protection harness was worn and dual lanyard anchored before elevated work on drilling platform.",
    "Hot work was performed with valid permit, trained fire watch man and fire extinguishers placed at site.",
    "Rigging gear was inspected and load chart verified before crane lift; certified banksman in position.",
    "Driver observed yard speed limit 15 kmph and used designated heavy vehicle route; pre-drive check completed.",
    "Gas testing completed prior to hot work in process unit; zero flammable hydrocarbons detected.",
    "Electrical job performed under work permit with circuit isolated, locked out and verified dead before work.",
    "Housekeeping issue: hand tools left on walkway after shift; area cleaned and tidied up immediately.",
    "Minor oil drip noticed from valve gland packing; drip tray placed and maintenance work order logged.",
    "One portable fire extinguisher found with broken tamper seal; replaced with fresh inspected unit immediately.",
    "Safety helmet visor had minor scratches; worker exchanged it for a new visor at safety store.",
    "Safety poster in compressor shelter was damaged by rain; replaced with fresh safety bulletin notice.",
    "Hand rail paint scratched on catwalk stairwell; reported for routine painting during scheduled turnaround.",
    "Rubber safety gloves showed minor surface wear; exchanged for new pair before starting routine task.",
    "Safety shoes boot laces worn out; employee collected new pair of safety boots from HSE store.",
    "Routine toolbox talk conducted before shift start; 12 workers attended and signed attendance sheet.",
    "Periodic inspection of eye wash station completed; water flow pressure tested normal.",
    "Noise level signage at generator house re-secured with new cable ties.",
    "Kaam shuru karne se pehle gas test kiya gaya aur sab kuch normal tha, koi khatra nahi mila.",
    "Driver followed yard speed limit and used designated route; no incidents reported.",
    "Work area cleaned and tools stowed in tool box after routine pump lubrication.",
    "Walkway lighting bulb replaced during daytime maintenance; area well illuminated.",
    "Emergency shower station tested weekly; water clarity and flow rate verified.",
    "Scaffold inspection tag updated by certified scaffold inspector after weekly check.",
    "PPE inspection completed for maintenance team; all hard hats, safety glasses and boots in order.",
    "Fire water hose box inspected; hose coupling lubricated and nozzle checked.",
    "Waste segregation bins emptied at field depot; trash disposed in designated bins.",
    "Kaam khatam hone ke baad sabhi tools jagah par rakh diye gaye aur area saaf kiya gaya.",
]

def generate_csv(output_path: str):
    rows = []
    
    # 150 SIF Positive cases (Repeat templates with variations)
    for i in range(150):
        tmpl = SIF_POSITIVE_TEMPLATES[i % len(SIF_POSITIVE_TEMPLATES)]
        prefix = f"Report RPT-S{i+1:04d} (Site {chr(65 + (i%5))}, Dept: Operations): "
        text = f"{prefix}{tmpl}"
        rows.append({
            "report_id": f"RPT-S{i+1:04d}",
            "description": text,
            "sif_potential": "Yes",
            "event_type": "Unsafe Act" if i % 2 == 0 else "Near Miss",
            "site": f"Site {chr(65 + (i%5))}"
        })
        
    # 350 Non-SIF cases
    for i in range(350):
        tmpl = NON_SIF_TEMPLATES[i % len(NON_SIF_TEMPLATES)]
        prefix = f"Report RPT-N{i+1:04d} (Site {chr(65 + (i%5))}, Dept: HSE): "
        text = f"{prefix}{tmpl}"
        rows.append({
            "report_id": f"RPT-N{i+1:04d}",
            "description": text,
            "sif_potential": "No",
            "event_type": "Unsafe Condition" if i % 2 == 0 else "Routine Observation",
            "site": f"Site {chr(65 + (i%5))}"
        })
        
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated dataset at {output_path} with {len(df)} records ({df['sif_potential'].value_counts().to_dict()}).")

if __name__ == "__main__":
    generate_csv("c:/Users/lspal/OneDrive/Desktop/SIH-SIF-Precursor-Detection/backend/app/data/oil_hsse_sif_dataset.csv")
