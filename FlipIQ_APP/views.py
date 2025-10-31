import json
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST
from .models import Profile, Deck, Card, Submission, Session, Participant
from django.utils import timezone
from django.db import transaction
from django.db.models import Prefetch, Q 


# ===============================
# 📦 EXISTING VIEWS
# ===============================

@csrf_exempt
@login_required
def publish_deck(request):
    """Create or update a deck with its cards (used in create_deck.html)."""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print("✅ Parsed JSON data:", data)

            deck_id = data.get("deckId")
            if deck_id:
                # --- Editing existing deck ---
                deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
                deck.title = data.get("deckTitle", deck.title)
                deck.time_interval = data.get("interval", deck.time_interval)
                deck.subject = data.get("subject", deck.subject)
                deck.visibility = data.get("visibility", deck.visibility)
                deck.save()
                deck.cards.all().delete()  # Clear old cards
                print(f"✏️ Updated deck: {deck.title}")
            else:
                # --- Creating a new deck ---
                deck = Deck.objects.create(
                    title=data.get("deckTitle", "Untitled Deck"),
                    owner=request.user,
                    time_interval=data.get("interval", "10 secs"),
                    subject=data.get("subject", "Other"),
                    visibility=data.get("visibility", "private"),
                )
                print(f"🆕 Created new deck: {deck.title}")

            for c in data.get("cards", []):
                Card.objects.create(
                    deck=deck,
                    front=c.get("front", ""),
                    back=c.get("back", ""),
                    choices=c.get("choices", [])
                )

            return JsonResponse({"success": True, "deck_id": deck.id})

        except Exception as e:
            print("❌ Error in publish_deck:", e)
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=405)


def home(request):
    """Show all public decks on homepage with search, participation info, and smart Flip logic."""
    query = request.GET.get("q", "")  # 🔍 Search query
    decks = Deck.objects.filter(visibility='public')

    # 🔍 If there's a search query, filter decks by title, subject, or owner's username
    if query:
        decks = decks.filter(
            Q(title__icontains=query) |
            Q(subject__icontains=query) |
            Q(owner__username__icontains=query)
        )

    public_decks = decks.order_by('-created_at')

    # Track user's submissions (for decks they've played)
    user_submissions = {}
    if request.user.is_authenticated:
        submissions = Submission.objects.filter(user=request.user).select_related('deck', 'session')
        for sub in submissions:
            user_submissions[sub.deck.id] = sub.session.id  # Store their latest session_id for that deck

    # Attach info to each deck (used in template)
    for deck in public_decks:
        deck.played = deck.id in user_submissions
        deck.session_id = user_submissions.get(deck.id)

    # 🟡 Handle Flip button click (?flip=<deck_id>)
    deck_id = request.GET.get('flip')
    if deck_id:
        deck = get_object_or_404(Deck, id=deck_id)
        user = request.user

        # 1️⃣ If user already played → redirect to their result
        submission = Submission.objects.filter(deck=deck, user=user).order_by('-submission_time').first()
        if submission and submission.session and submission.session.is_started:
            return redirect('deck_result', deck_id=deck.id, session_id=submission.session.id)

        # 2️⃣ If session is active → go to play screen
        active_session = Session.objects.filter(deck=deck, is_active=True, is_started=True).first()
        if active_session:
            return redirect('play_deck', deck_id=deck.id, session_id=active_session.id)

        # 3️⃣ Otherwise → deck not started page
        return redirect('deck_not_started', deck_id=deck.id)

    return render(request, 'FlipIQ_APP/home.html', {
        'public_decks': public_decks,
        'query': query,
    })



@require_http_methods(["GET", "POST"])
def signup(request):
    """Handles user signup with role selection."""
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = form.cleaned_data.get('username', '').strip()
            user.save()

            role = request.POST.get('role', Profile.ROLE_STUDENT)
            if role not in dict(Profile.ROLE_CHOICES):
                role = Profile.ROLE_STUDENT
            Profile.objects.create(user=user, role=role)

            login(request, user)
            messages.success(request, "Account created successfully! Welcome to FlipIQ.")
            return redirect('home')
        else:
            print("Form not valid:", form.errors)
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def profile(request):
    """Display user profile with created decks and recent played history."""
    created_decks = Deck.objects.filter(owner=request.user).order_by('-created_at')

    # 🕒 Get user's most recent submissions (limit to last 10)
    recent_submissions = (
        Submission.objects.filter(user=request.user)
        .select_related('deck', 'session')
        .order_by('-submission_time')[:10]
    )

    return render(request, 'FlipIQ_APP/profile.html', {
        'created_decks': created_decks,
        'recent_submissions': recent_submissions,
    })


@login_required
def create_deck(request):
    """Render deck creation page. Works for both new & edit modes."""
    return render(request, 'FlipIQ_APP/create_deck.html')


@login_required
def edit_deck(request, deck_id):
    """Render create_deck page but for editing an existing deck."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    return render(request, 'FlipIQ_APP/create_deck.html', {'deck_id': deck.id})


@login_required
def get_deck_data(request, deck_id):
    """Returns deck info + cards in JSON for pre-filling."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    cards = list(deck.cards.values('id', 'front', 'back', 'choices'))
    data = {
        "id": deck.id,
        "title": deck.title,
        "interval": deck.time_interval,
        "subject": deck.subject,
        "visibility": deck.visibility,
        "cards": cards
    }
    return JsonResponse(data)


@login_required
def delete_deck(request, deck_id):
    """Delete a deck owned by the user."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    if request.method == 'POST':
        deck.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def control_panel_deck(request, deck_id):
    """Render the Control Panel for deck management."""
    deck = get_object_or_404(Deck, id=deck_id)
    if deck.owner != request.user:
        return redirect('home')

    # ✅ Fetch real submissions from the database
    submissions = (
        deck.submissions
        .select_related('user', 'session')
        .order_by('-submission_time')
    )

    # ✅ Compute total distinct participants
    total_students = submissions.values('user').distinct().count()

    # ✅ Compute average completion rate
    total_submissions = submissions.count()
    avg_completion = round(
        sum(s.percentage() for s in submissions) / total_submissions,
        1
    ) if total_submissions > 0 else 0

    # ✅ Keep your existing active session redirect
    active_session = Session.objects.filter(deck=deck, is_active=True, host=request.user).first()
    if active_session and active_session.is_started:
        return redirect('report_view', deck_id=deck.id, session_id=active_session.id)

    return render(request, 'FlipIQ_APP/control_panel_decks.html', {
        'deck': deck,
        'submissions': submissions,
        'total_students': total_students,
        'avg_completion': avg_completion,
        'has_submissions': submissions.exists()
    })



# ===============================
# ⚙️ NEW API ENDPOINTS (for real-time deck control)
# ===============================

@csrf_exempt
@login_required
def update_deck_title(request, deck_id):
    """AJAX: Update deck title instantly."""
    if request.method == 'POST':
        deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
        data = json.loads(request.body.decode("utf-8"))
        new_title = data.get("title", "").strip()
        if not new_title:
            return JsonResponse({"success": False, "error": "Empty title"}, status=400)
        deck.title = new_title
        deck.save()
        return JsonResponse({"success": True, "title": deck.title})
    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
@login_required
def add_card(request, deck_id):
    """AJAX: Add a new card dynamically."""
    if request.method == 'POST':
        deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
        card = Card.objects.create(deck=deck, front="", back="", choices=[])
        return JsonResponse({"success": True, "card_id": card.id})
    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
@login_required
def update_card(request, card_id):
    """AJAX: Update a card’s content instantly."""
    if request.method == 'POST':
        card = get_object_or_404(Card, id=card_id, deck__owner=request.user)
        data = json.loads(request.body.decode("utf-8"))
        card.front = data.get("front", card.front)
        card.back = data.get("back", card.back)
        card.choices = data.get("choices", card.choices)
        card.save()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
@login_required
def delete_card(request, card_id):
    """AJAX: Delete a specific card."""
    if request.method == 'POST':
        card = get_object_or_404(Card, id=card_id, deck__owner=request.user)
        card.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid method"}, status=405)


@login_required
def fetch_report(request, deck_id):
    """AJAX: Fetch latest participation data for report (🔧 placeholder for now)."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)

    # TODO: Replace with real Submission model data later
    submissions = [
        {"name": "Pinkie Pie", "time": "13:16", "date": "mm/dd/year", "score": "1/2", "percent": "50%"},
        {"name": "Twilight Sparkle", "time": "13:20", "date": "mm/dd/year", "score": "2/2", "percent": "100%"},
        {"name": "Flutter Shy", "time": "13:29", "date": "mm/dd/year", "score": "1/2", "percent": "50%"},
    ]

    return JsonResponse({"has_submissions": True, "submissions": submissions})


@csrf_exempt
@login_required
def start_deck(request, deck_id):
    """AJAX: Mark the deck as started (or active)."""
    if request.method == 'POST':
        deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
        deck.is_active = True  # you can add this field in model if not yet existing
        deck.save()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid method"}, status=405)

# ====================================
# 🟡 LIVE SESSION CONTROLS (Host side)
# ====================================

@csrf_exempt
@login_required
def start_quiz(request, deck_id):
    """Activate a running session (when host clicks 'Start Now')."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    session = Session.objects.filter(deck=deck, is_active=True).first()

    if not session:
        return JsonResponse({"error": "No active session found"}, status=404)

    session.is_started = True
    session.save()

    return JsonResponse({
        "success": True,
        "redirect_url": f"/deck/{deck.id}/report/{session.id}/"
    })


@csrf_exempt
@login_required
def end_session(request, deck_id):
    """End the current active session for this deck."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    session = Session.objects.filter(deck=deck, is_active=True).last()

    if not session:
        return JsonResponse({"success": False, "error": "No active session found"})

    session.is_active = False
    session.save()

    return JsonResponse({"success": True})


@login_required
def get_session_status(request, deck_id):
    """Return all participants and progress info for the active session."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    session = Session.objects.filter(deck=deck, is_active=True).last()
    if not session:
        return JsonResponse({"active": False})

    participants = Participant.objects.filter(session=session).select_related("user")
    data = [
        {
            "name": f"{p.user.first_name} {p.user.last_name}".strip() or p.user.username,
            "progress": p.progress,
            "total": p.total_cards,
        }
        for p in participants
    ]

    return JsonResponse({"active": True, "code": session.code, "participants": data})


@csrf_exempt
@login_required
def kick_participant(request, participant_id):
    """Kick a participant from the live session."""
    try:
        participant = get_object_or_404(Participant, id=participant_id)
        participant.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
@login_required
def join_deck_by_code(request):
    """Join an active session using a 6-digit code."""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            code = data.get("code", "").strip()
            if not code:
                return JsonResponse({"success": False, "error": "No code entered"})

            session = Session.objects.filter(code=code, is_active=True).first()
            if not session:
                return JsonResponse({"success": False, "error": "Invalid or inactive code"})

            # Prevent duplicates
            participant, created = Participant.objects.get_or_create(
                session=session, user=request.user,
                defaults={"total_cards": session.deck.cards.count()}
            )

            return JsonResponse({
                "success": True,
                "deck_id": session.deck.id,
                "session_id": session.id,
                "deck_title": session.deck.title
            })

        except Exception as e:
            print("❌ join_deck_by_code error:", e)
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"error": "Invalid request method"}, status=405)

@login_required
def join_deck_page(request):
    return render(request, 'FlipIQ_APP/join_deck.html')

@login_required
def check_session_status(request, code):
    """Participants poll this endpoint to check if host started."""
    session = get_object_or_404(Session, code=code)
    return JsonResponse({"is_started": session.is_started})

from django.shortcuts import render, get_object_or_404
from .models import Deck, Session

@login_required
def join_waiting(request, deck_id, session_id):
    deck = get_object_or_404(Deck, id=deck_id)
    session = get_object_or_404(Session, id=session_id, deck=deck)

    return render(request, 'FlipIQ_APP/join_waiting.html', {
        'deck': deck,
        'session': session,  # ✅ this line is required
    })

def leave_deck(request, deck_id, session_id):
    session = get_object_or_404(Session, id=session_id, deck_id=deck_id)
    if request.user.is_authenticated:
        Participant.objects.filter(session=session, user=request.user).delete()
    return redirect('home') 

@login_required
def get_participants(request, deck_id, session_id):
    """Return the list of participants for a given session."""
    from .models import Participant  # ensure it's imported properly
    session = get_object_or_404(Session, id=session_id, deck_id=deck_id)
    participants = Participant.objects.filter(session=session).select_related("user")

    data = [
        {
            "name": f"{p.user.first_name} {p.user.last_name}".strip() or p.user.username
        }
        for p in participants
    ]

    return JsonResponse({"participants": data})

# PLAY view: render the play screen for a participant
@login_required
def play_deck(request, deck_id, session_id):
    deck = get_object_or_404(Deck, id=deck_id)
    session = get_object_or_404(Session, id=session_id, deck=deck, is_active=True)

    # Ensure participant entry exists (create if not)
    participant, created = Participant.objects.get_or_create(
        session=session,
        user=request.user,
        defaults={'total_cards': deck.cards.count(), 'progress': 0}
    )
    # Ensure total_cards kept up-to-date
    if participant.total_cards != deck.cards.count():
        participant.total_cards = deck.cards.count()
        participant.save()

    # Ensure Submission exists for this session+user (we use this as the live score container)
    submission, _ = Submission.objects.get_or_create(
        deck=deck, session=session, user=request.user,
        defaults={'score': 0, 'total': deck.cards.count()}
    )

    if not session or not session.is_started:
        # ⚠️ Deck not started yet
        return render(request, 'FlipIQ_APP/deck_not_started.html', {'deck': deck})


    # Prepare card data for the front-end
    cards = list(deck.cards.values('id', 'front', 'back', 'choices'))
    # time interval -> convert to seconds (if stored as "10 secs", "1 min" etc.)
    interval_str = deck.time_interval or "10 secs"
    # simple parser:
    def interval_to_seconds(s):
        s = s.strip().lower()
        if "min" in s: 
            try:
                return int(''.join([c for c in s if c.isdigit()])) * 60
            except: return 60
        if "sec" in s:
            try:
                return int(''.join([c for c in s if c.isdigit()]))
            except: return 10
        try:
            return int(s)
        except:
            return 10

    interval_seconds = interval_to_seconds(interval_str)

    return render(request, 'FlipIQ_APP/play_deck.html', {
        'deck': deck,
        'session': session,
        'participant': participant,
        'submission': submission,
        'cards_json': json.dumps(cards),
        'interval_seconds': interval_seconds,
        'cards_count': len(cards)
    })


# AJAX endpoint: participant submits an answer for one card
@csrf_exempt
@login_required
@require_POST
def submit_answer(request, deck_id):
    """
    Expected JSON:
    {
      "session_id": 2,
      "card_id": 17,
      "choice": "4"
    }
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        session_id = int(data.get('session_id'))
        card_id = int(data.get('card_id'))
        choice = data.get('choice', '').strip()
    except Exception as e:
        return JsonResponse({"success": False, "error": "Invalid payload"}, status=400)

    session = get_object_or_404(Session, id=session_id, deck_id=deck_id, is_active=True)
    card = get_object_or_404(Card, id=card_id, deck_id=deck_id)

    # find participant
    participant = Participant.objects.filter(session=session, user=request.user).first()
    if not participant:
        # create participant if not exists (rare)
        participant = Participant.objects.create(session=session, user=request.user, total_cards=session.deck.cards.count(), progress=0)

    # determine correctness: card.back holds correct answer (string)
    is_correct = (str(card.back).strip() == str(choice).strip())

    # update participant and submission atomically
    with transaction.atomic():
        # increment progress but ensure does not exceed total_cards
        participant.progress = min(participant.total_cards, participant.progress + 1)
        participant.save()

        submission, created = Submission.objects.get_or_create(deck=session.deck, session=session, user=request.user,
                                                               defaults={'score': 0, 'total': session.deck.cards.count()})
        if is_correct:
            submission.score = submission.score + 1
        # keep total in-sync
        submission.total = session.deck.cards.count()
        submission.save()

    return JsonResponse({
        "success": True,
        "is_correct": is_correct,
        "progress": participant.progress,
        "total": participant.total_cards,
        "score": submission.score
    })

@login_required
def report_view(request, deck_id, session_id):
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
    session = get_object_or_404(Session, id=session_id, deck=deck)

    participants = Participant.objects.filter(session=session)
    return render(request, "report_view.html", {
        "deck": deck,
        "session": session,
        "participants": participants,
        
    })

@csrf_exempt
@login_required
def start_session(request, deck_id):
    """Create a new live session and return a join code."""
    deck = get_object_or_404(Deck, id=deck_id, owner=request.user)

    # End any existing sessions for this deck
    Session.objects.filter(deck=deck, is_active=True).update(is_active=False)

    # Create a new session
    session = Session.objects.create(deck=deck, host=request.user)
    return JsonResponse({"success": True, "code": session.code, "session_id": session.id})


@csrf_exempt
@login_required
def activate_flag(request, deck_id):
    """Activate the live quiz (when host clicks 'Start Now')."""
    if request.method == 'POST':
        deck = get_object_or_404(Deck, id=deck_id, owner=request.user)
        session = Session.objects.filter(deck=deck, is_active=True).first()
        if not session:
            return JsonResponse({"success": False, "error": "No active session found."})

        session.is_started = True
        session.save()

        # ✅ Return session_id for redirect
        return JsonResponse({"success": True, "session_id": session.id})
        
    return JsonResponse({"error": "Invalid method"}, status=405)


def check_session_status(request, code):
    """Students call this to check if the host has started the quiz."""
    try:
        session = Session.objects.get(code=code)
        return JsonResponse({
            "is_started": session.is_started,
            "active": session.is_active,
        })
    except Session.DoesNotExist:
        raise Http404("Session not found")

@login_required
def deck_status(request, deck_id):
    """
    Returns the current state of the deck/session for the player.
    Used to check if the quiz is done or session is still active.
    """
    deck = get_object_or_404(Deck, id=deck_id)
    session = Session.objects.filter(deck=deck, is_active=True).first()
    if not session:
        return JsonResponse({"active": False, "is_started": False})

    return JsonResponse({
        "active": session.is_active,
        "is_started": session.is_started,
    })

@login_required
def deck_result(request, deck_id, session_id):
    deck = get_object_or_404(Deck, id=deck_id)
    session = get_object_or_404(Session, id=session_id, deck=deck)
    submission = Submission.objects.filter(deck=deck, session=session, user=request.user).last()

    correct = submission.score if submission else 0
    wrong = (submission.total - submission.score) if submission else 0

    return render(request, "FlipIQ_APP/deck_result.html", {
        "deck": deck,
        "session": session,
        "correct": correct,
        "wrong": wrong
    })

@csrf_exempt
@login_required
def reset_progress(request, deck_id, session_id):
    """
    Reset the participant's score and progress so they can replay the deck.
    """
    deck = get_object_or_404(Deck, id=deck_id)
    session = get_object_or_404(Session, id=session_id, deck=deck, is_active=True)
    
    try:
        participant = Participant.objects.get(session=session, user=request.user)
        submission = Submission.objects.filter(deck=deck, session=session, user=request.user).last()

        # Reset participant progress
        participant.progress = 0
        participant.save()

        # Reset submission score
        if submission:
            submission.score = 0
            submission.save()

        return JsonResponse({"success": True})
    except Participant.DoesNotExist:
        return JsonResponse({"success": False, "error": "Participant not found"}, status=404)


@login_required
def deck_not_started(request, deck_id):
    """Display a message when a deck session is not yet started."""
    deck = get_object_or_404(Deck, id=deck_id)
    return render(request, 'FlipIQ_APP/deck_not_started.html', {'deck': deck})
