import requests
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


# ============================================================
# CONFIGURATION
# ============================================================

SALONKEE_URL = "https://salonkee.be/api/availability/v2/public"

SALON_ID = 133
SERVICE_ID = 5651
SERVICE_ITEM_ID = 8443
SERVICE_ITEM_REF = "5651-8443-0"

DISCORD_WEBHOOK_URL = ""  #TODO: Create a discord webhook and past the hook url here

STATE_FILE = "state.json"

ACTIVATE_MENTIONS = False


# ============================================================
# ETAT
# ============================================================

def load_state():
    """
    Charge l'état sauvegardé.

    Retourne :
        {
            "slots": set(...),
            "last_daily_summary": "YYYY-MM-DD"
        }

    Si le fichier n'existe pas, retourne None.
    """

    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        slots = set(
            tuple(slot)
            for slot in data.get("slots", [])
        )

        last_daily_summary = data.get("last_daily_summary")

        return {
            "slots": slots,
            "last_daily_summary": last_daily_summary
        }

    except Exception as e:
        print(f"Impossible de lire {STATE_FILE}: {e}")
        return None


def save_state(slots, last_daily_summary):
    """
    Sauvegarde les créneaux actuellement disponibles
    et la date du dernier résumé quotidien.
    """

    data = {
        "slots": [
            list(slot)
            for slot in slots
        ],
        "last_daily_summary": last_daily_summary
    }

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# SALONKEE
# ============================================================

def get_available_slots(start_date, end_date):
    """
    Recherche les créneaux disponibles sur Salonkee.
    """

    payload = {
        "salonID": 0,  # TODO: Paste the salon ID and booking informations here
        "usageMode": "strict",
        "startDate": start_date,
        "endDate": end_date,
        "bookingItems": [
            {
                "type": "service",
                "serviceItemRef": "0",
                "serviceID": 0,
                "serviceItemID": 0,
                "selectedEmployeeIDs": None
            }
        ],
        "existingBookingID": None
    }

    response = requests.post(
        SALONKEE_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    slots = []

    for day, day_data in data.get("result", {}).items():

        for timeslot in day_data.get("availableTimeslots", []):

            slots.append((
                day,
                timeslot["start"],
                timeslot["end"]
            ))

    return slots


# ============================================================
# FORMATAGE
# ============================================================

def format_search_info(
    search_datetime,
    start_date,
    end_date
):
    """
    Formatage de l'en-tête des messages Discord.
    """

    return (
        "## 🔎 Recherche Salonkee\n"
        "```text\n"
        f"Recherche : {search_datetime}\n"
        f"Période   : {start_date} → {end_date}\n"
        "```"
    )


def format_slots(slots):
    """
    Formate une liste de créneaux dans un bloc de code Discord.
    """

    if not slots:
        return "Aucun créneau disponible."

    sorted_slots = sorted(slots)

    lines = []

    for slot_date, start, end in sorted_slots:

        lines.append(
            f"{slot_date}    {start} → {end}"
        )

    return (
        "```text\n"
        "DATE          HEURE\n"
        "────────────────────────\n"
        + "\n".join(lines)
        + "\n```"
    )


# ============================================================
# DISCORD
# ============================================================

def send_discord_notification(
    message,
    search_datetime,
    start_date,
    end_date,
    mention_everyone=False
):
    """
    Envoie un message sur Discord.
    """

    header = format_search_info(
        search_datetime,
        start_date,
        end_date
    )

    content = (
        header
        + "\n\n"
        + message
    )

    if mention_everyone and ACTIVATE_MENTIONS:
        content = "@everyone\n\n" + content

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "content": content,
            "allowed_mentions": {
                "parse": ["everyone"]
                if (mention_everyone and ACTIVATE_MENTIONS)
                else []
            }
        },
        timeout=30
    )

    response.raise_for_status()


# ============================================================
# RECHERCHE
# ============================================================

def check_availability():
    """
    Effectue une recherche et détermine si une notification
    Discord doit être envoyée.
    """

    # --------------------------------------------------------
    # DATES
    # --------------------------------------------------------

    today = date.today()

    next_month = today + relativedelta(months=1)

    start_date = today.isoformat()
    end_date = next_month.isoformat()

    current_date_string = today.isoformat()

    search_datetime = datetime.now().strftime(
        "%d/%m/%Y à %H:%M:%S"
    )

    print()
    print("========================================")
    print("Recherche Salonkee")
    print(f"Recherche : {search_datetime}")
    print(f"Période   : {start_date} -> {end_date}")
    print("========================================")


    # --------------------------------------------------------
    # RECHERCHE SALONKEE
    # --------------------------------------------------------

    try:

        current_slots_list = get_available_slots(
            start_date,
            end_date
        )

        current_slots = set(current_slots_list)

        print(
            f"Créneaux disponibles : "
            f"{len(current_slots)}"
        )

    except Exception as e:

        print(f"Erreur pendant la recherche : {e}")

        try:

            send_discord_notification(
                (
                    "❌ **Erreur pendant la recherche**\n\n"
                    "```text\n"
                    f"{e}\n"
                    "```"
                ),
                search_datetime,
                start_date,
                end_date
            )

        except Exception as discord_error:

            print(
                "Impossible d'envoyer l'erreur sur Discord : "
                f"{discord_error}"
            )

        return


    # --------------------------------------------------------
    # CHARGEMENT DE L'ETAT
    # --------------------------------------------------------

    state = load_state()


    # ========================================================
    # PREMIER LANCEMENT TOUT COURT
    # ========================================================

    if state is None:

        print("Premier lancement du programme.")

        # Tous les créneaux présents sont enregistrés comme
        # état initial. Ils ne sont PAS considérés comme
        # nouveaux pour la notification.

        save_state(
            current_slots,
            current_date_string
        )

        if current_slots:

            message = (
                "## 📋 Résumé des créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )

        else:

            message = (
                "## 📋 Résumé des créneaux disponibles\n\n"
                "Aucun créneau disponible actuellement."
            )

        try:

            send_discord_notification(
                message,
                search_datetime,
                start_date,
                end_date,
                mention_everyone=False
            )

            print("Résumé initial envoyé sur Discord.")

        except Exception as e:

            print(f"Erreur Discord : {e}")

        return


    # ========================================================
    # COMPARAISON AVEC LE DERNIER ETAT
    # ========================================================

    known_slots = state["slots"]

    # Créneaux apparus depuis le dernier check
    new_slots = current_slots - known_slots

    # Créneaux qui étaient présents au dernier check
    # mais qui ne le sont plus maintenant
    removed_slots = known_slots - current_slots

    # Premier check de la journée
    is_first_check_of_day = (
        state["last_daily_summary"] != current_date_string
    )

    print(
        f"Nouveaux créneaux : "
        f"{len(new_slots)}"
    )

    print(
        f"Créneaux supprimés  : {len(removed_slots)}"
    )

    print(
        f"Premier check de la journée : "
        f"{is_first_check_of_day}"
    )


    # ========================================================
    # PREMIER CHECK DE LA JOURNEE
    # ========================================================

    if is_first_check_of_day:

        print("Envoi du résumé quotidien.")

        # ----------------------------------------------------
        # NOUVEAUX + SUPPRIMES
        # ----------------------------------------------------

        if new_slots and removed_slots:

            message = (
                "## 🚨 Nouveaux créneaux disponibles\n\n"
                f"{format_slots(new_slots)}\n\n"

                "## ❌ Créneaux devenus indisponibles\n\n"
                f"{format_slots(removed_slots)}\n\n"

                "## 📋 Résumé de tous les créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )

            mention_everyone = True

        # ----------------------------------------------------
        # NOUVEAUX CRENEAUX UNIQUEMENT
        # ----------------------------------------------------

        elif new_slots:

            message = (
                "## 🚨 Nouveaux créneaux disponibles\n\n"
                f"{format_slots(new_slots)}\n\n"
                "## 📋 Résumé de tous les créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )

            mention_everyone = True

        # ----------------------------------------------------
        # SUPPRIMES UNIQUEMENT
        # ----------------------------------------------------

        elif removed_slots:

            message = (
                "## ❌ Créneaux devenus indisponibles\n\n"
                f"{format_slots(removed_slots)}\n\n"

                "## 📋 Résumé des créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )

            mention_everyone = False

        # ----------------------------------------------------
        # AUCUN CHANGEMENT + CRENEAUX DISPONIBLES
        # ----------------------------------------------------

        elif current_slots:

            message = (
                "## 📋 Résumé des créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )

            mention_everyone = False

        # ----------------------------------------------------
        # AUCUN CRENEAU
        # ----------------------------------------------------

        else:

            message = (
                "## 📋 Résumé des créneaux disponibles\n\n"
                "Aucun créneau disponible actuellement."
            )

            mention_everyone = False


        try:

            send_discord_notification(
                message,
                search_datetime,
                start_date,
                end_date,
                mention_everyone=mention_everyone
            )

            print("Résumé quotidien envoyé sur Discord.")

        except Exception as e:

            print(f"Erreur Discord : {e}")


        # La journée a maintenant eu son résumé
        save_state(
            current_slots,
            current_date_string
        )

        return


    # ========================================================
    # CHECKS NORMAUX
    # ========================================================

    if new_slots:

        print("Nouveaux créneaux détectés !")

        # ----------------------------------------------------
        # NOUVEAUX CRENEAUX + SUPPRIMES
        # ----------------------------------------------------

        if removed_slots:

            message = (
                "## 🚨 Nouveaux créneaux disponibles\n\n"
                f"{format_slots(new_slots)}\n\n"

                "## ❌ Créneaux devenus indisponibles\n\n"
                f"{format_slots(removed_slots)}\n\n"

                "## 📋 Résumé de tous les créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )

        else:

            message = (
                "## 🚨 Nouveaux créneaux disponibles\n\n"
                f"{format_slots(new_slots)}\n\n"

                "## 📋 Résumé de tous les créneaux disponibles\n\n"
                f"{format_slots(current_slots)}"
            )


        try:

            send_discord_notification(
                message,
                search_datetime,
                start_date,
                end_date,
                mention_everyone=True
            )

            print("Notification de nouveaux créneaux envoyée.")

        except Exception as e:

            print(f"Erreur Discord : {e}")

    # --------------------------------------------------------
    # CRENEAUX SUPPRIMES MAIS AUCUN NOUVEAU
    # --------------------------------------------------------

    elif removed_slots:

        print("Des créneaux sont devenus indisponibles.")

        message = (
            "## ❌ Créneaux devenus indisponibles\n\n"
            f"{format_slots(removed_slots)}\n\n"

            "## 📋 Résumé des créneaux disponibles\n\n"
            f"{format_slots(current_slots)}"
        )

        try:

            send_discord_notification(
                message,
                search_datetime,
                start_date,
                end_date,
                mention_everyone=False
            )

            print(
                "Notification de créneaux supprimés envoyée."
            )

        except Exception as e:

            print(f"Erreur Discord : {e}")

    else:

        # Aucun nouveau créneau :
        # aucun message Discord.

        print(
            "Aucun nouveau créneau. "
            "Aucun message Discord envoyé."
        )


    # --------------------------------------------------------
    # SAUVEGARDE DU NOUVEL ETAT
    # --------------------------------------------------------

    save_state(
        current_slots,
        state["last_daily_summary"]
    )


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():

    print("========================================")
    print("       SALONKEE AVAILABILITY WATCHER")
    print("========================================")
    print()
    print("Programme démarré.")
    print()

    check_availability()


if __name__ == "__main__":
    main()