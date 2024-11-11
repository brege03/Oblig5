from flask import Flask, url_for, render_template, request, redirect, session
import pandas as pd  # Legger til pandas for å lese fra Excel

from kgcontroller import (form_to_object_soknad, insert_soknad, commit_all, select_alle_barnehager, select_alle_soknader)

app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY'  # nødvendig for session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barnehager')
def barnehager():
    # Henter informasjon om alle barnehager
    information = select_alle_barnehager()
    return render_template('barnehager.html', data=information)

@app.route('/behandle', methods=['GET', 'POST'])
def behandle():
    if request.method == 'POST':
        # Henter data fra skjemaet
        sd = request.form
        print(sd)
        
        # Lager en søknad basert på skjemaet
        soknad_objekt = form_to_object_soknad(sd)
        
        # Setter inn søknaden i "databasen"
        insert_soknad(soknad_objekt)
        
        # Lagre skjemaopplysningene i session for senere bruk
        session['information'] = sd

        # Vurderer status basert på antall ledige plasser og fortrinnsrett
        ledige_plasser = 5  # Dette bør hentes dynamisk fra databasen
        status = "AVSLAG"

        if ledige_plasser > 0:
            status = "TILBUD"
        elif (sd.get('fortrinnsrett_barnevern') or 
              sd.get('fortrinnsrett_sykdom_i_familien') or 
              sd.get('fortrinnsrett_sykdome_paa_barnet')):
            status = "Fortrinnsrett, venter på ledig plass"

        # Går videre til svar-siden og gir status
        return render_template('svar.html', data=sd, status=status)
    else:
        return render_template('soknad.html')

@app.route('/svar')
def svar():
    if 'information' in session:
        # Henter informasjonen fra session
        information = session['information']
        
        # Viser informasjonen og gir standard status (dette vil vanligvis allerede være gjort i /behandle)
        status = "AVSLAG"  # Standardverdi som kan endres basert på ledige plasser
        return render_template('svar.html', data=information, status=status)
    else:
        # Hvis det ikke er noen informasjon i session, går tilbake til hovedsiden
        return redirect(url_for('index'))

@app.route('/commit')
def commit():
    # Skriver alle endringer til Excel-filen for å sikre at dataene er lagret
    commit_all()

    # Leser alle data fra kgdata.xlsx
    data_path = 'kgdata.xlsx'  # Sørg for at denne er riktig plassert og tilgjengelig
    try:
        foresatte_df = pd.read_excel(data_path, sheet_name='foresatt')
        barn_df = pd.read_excel(data_path, sheet_name='barn')
        soknad_df = pd.read_excel(data_path, sheet_name='soknad')
    except FileNotFoundError:
        return "Feil: Excel-filen 'kgdata.xlsx' ble ikke funnet."
    except Exception as e:
        return f"Feil ved lesing av Excel-filen: {e}"

    # Sender dataene til commit.html for visning
    return render_template('commit.html', foresatte=foresatte_df.to_dict(orient='records'),
                           barn=barn_df.to_dict(orient='records'),
                           soknader=soknad_df.to_dict(orient='records'))

@app.route('/soeknader')
def soeknader():
    # Henter alle søknader fra "databasen"
    alle_soknader = select_alle_soknader()
    ledige_plasser = 5  # Dette bør justeres dynamisk for å reflektere faktisk antall ledige plasser fra databasen
    
    # Beregner status for hver søknad basert på ledige plasser og fortrinnsrett
    for soknad in alle_soknader:
        if ledige_plasser > 0:
            soknad.status = "TILBUD"
            ledige_plasser -= 1
        elif soknad.fr_barnevern or soknad.fr_sykd_familie or soknad.fr_sykd_barn:
            soknad.status = "Fortrinnsrett, venter på ledig plass"
        else:
            soknad.status = "AVSLAG"

    # Viser alle søknader i soeknader.html
    return render_template('soeknader.html', soknader=alle_soknader)

if __name__ == "__main__":
    app.run(debug=False)