import traceback

from app import app, db
from mod_api import models
from tools.pong_tools import *
from tools.general_purpose_tools import *


def create_league(league_csv):    
    # create league instance
    try:
        league_name = league_csv.split('.')[0] ## small back upon creation with non existent csv
        league = models.League(name=league_name)
        db.session.add(league)
        db.session.commit()
    except:
        db.session.rollback()
        # traceback.print_exc()
        return

    # create and add players to the league
    players = list()
    with open(league_csv, 'rb') as csvfile:
        player_reader = csv.DictReader(csvfile)
        for row in player_reader:
            try:
                validate_email(email=row['Email'], name=row['Full_Name'])
                players.append(row)
                player = models.Player(league=league, email=row['Email'], name=row['Full_Name'])
                db.session.add(player)
                db.session.commit()
            # block duplicates
            except:
                print row['Full_Name'], 'creation failed.'
                db.session.rollback()
                # traceback.print_exc()     

    
def generate_matches(league_id, test=False):
    try:
        # fetch league and update round count
        league = models.League.get_league_by_id(league_id)
        if not test:
            league.round_count = league.round_count + 1            

        # update player stats and fetch players of league in descending order of net wins
        all_players = league.get_all_players_sorted()
        ref_points = all_players[0].net_wins
        min_points = all_players[-1].net_wins

        # first-middle matching
        unmatched_player = None
        while ref_points >= min_points:
            current_players = list()
            for i in range(len(all_players)):
                player_points = all_players[i].net_wins
                if player_points == ref_points:
                    current_players.append(all_players[i])
                elif player_points < ref_points:
                    break
            if current_players:
                unmatched_player = match_em(league, current_players, unmatched_player)
            ref_points = ref_points - 1

        # Case of odd number of players; generate bye match (no opponent)
        if unmatched_player:
            new_match = models.Match_(league, unmatched_player.name, app.config['BYE'])
            db.session.add(new_match)            

        export_matches(league)
        db.session.commit()
    except:
        db.session.rollback()
        print 'Failed to generate new matches for', league.name, 'round', league.round_count
        traceback.print_exc()  
        return


def generate_leaderboard(league_id, results_csv):
    try:
        process_results(results_csv)
        league = models.League.get_league_by_id(league_id)

        # generate leaderboard csv
        csv_name = league.name + ' - Leaderboard Round ' + str(league.round_count) + '.csv'
        league_players = league.get_all_players_sorted()
        format_players(league_players)
        keys = models.Player.key_fields()
        csv_export(csv_name, league_players, keys)
    except:
        db.session.rollback()
        print 'Failed to generate leaderboard for', league.name, 'round', league.round_count
        traceback.print_exc()  
        return

def delete_last_matches(league_id):
    league = models.League.get_league_by_id(league_id)
    target_matches = models.Match_.query.filter_by(league=league_id, round_count=round_count)
    for match in target_matches: 
        match.delete()

def add_player(email, name, league_id):
    try:
        league = models.League.get_league_by_id(int(league_id))
        player = models.Player(league, email, name)
        player.commit(insert=True)
        print name, 'successfully added.'
    except:
        db.session.rollback()
        traceback.print_exc()  
        return

def delete_player(player_email):
    try:
        player = models.Player.get_player_by_email(player_email)
        name = player.name
        player.delete()
        print name, 'successfully deleted.'
    except:
        db.session.rollback()
        traceback.print_exc()  
        return

def get_player_stats(player_email):
    try:
        player = models.Player.get_player_by_email(player_email)
        stats = dict(league=player.league.name, victories=player.games_won, losses=player.games_lost,
                     sets_won=player.sets_won, sets_lost=player.sets_lost, penalty_points=player.penalty_points, rating=player.rating)
        print '\nPlayer stats of', player.name, ':\n'
        for k,v in sorted(stats.iteritems()):
            print k, '=', v
    except:
        print 'Invalid email. Please enter a valid email.'
        # traceback.print_exc()  
        return    


"""
Next steps:
1) Revamp processes: 1.2, 1.3, 2.3
2) Unit testing: Test Match Generation and Result Processing 
2.5) proper deletion of matchups
3) resolve League backref to matches
4) Proper deletion of players
5) Handle Repeated Matchups
6) adjust get stats format and include net wins and net losses
"""


# Debt:
# adjust repeated matches 
# add ssh key to github
# elo system
# compute player stats programmatically (also adjust line 50 in this file)