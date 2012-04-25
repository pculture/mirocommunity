;var localtv_contests;jQuery(function($){
    var contests = localtv_contests = [],
        activeClass = 'button-selected';
    function Contest(parent){
        contest = this
        contest.parent = $(parent);
        contest.data = {
            'contestvideo': contest.parent.attr('data-contestvideo'),
            'user': contest.parent.attr('data-user'),
        };
        contest.uris = {
            'vote-list-uri': '/api/v1/contestvote/',
            'contestvideo-uri': '/api/v1/contestvideo/' + contest.data['contestvideo'] + '/',
            'user-uri': '/api/v1/user/' + contest.data['user'] + '/',
        };
        contest.downvotes = contest.parent.attr('data-downvotes') == "1" ? true : false;
        contest.voteButtons = {
            '1': $('<button value="1">Vote up</button>'),
            '-1': $('<button value="-1">Vote down</button>'),
        };
        contest.vote = '0'
        $.getJSON(contest.uris['vote-list-uri'],
                  {
                      'user': contest.data['user'],
                      'contestvideo': contest.data['contestvideo'],
                  },
                  function(data){
                      contest.init();
                      contest.handleData(data['objects'][0]);
                  });
        contest.init = function(){
            contest.parent.append(contest.voteButtons['1']);
            if (contest.downvotes) {
                contest.parent.append(contest.voteButtons['-1']);
            };
        };
        contest.handleData = function(data){
            contest.voteData = data;
            if (contest.voteData != undefined) {
                contest.setVote(contest.voteData['vote']);
            };
        };
        contest.setVote = function(vote){
            if (vote != contest.vote) {
                old_button = contest.voteButtons[contest.vote];
                if (old_button != undefined) {
                    old_button.removeClass(activeClass);
                };
                new_button = contest.voteButtons[vote];
                if (new_button != undefined) {
                    new_button.addClass(activeClass);
                };
                contest.vote = vote
        };
        contest.sendVote = function(){
                if (contest.vote == '0'){
                    if (contest.voteData != undefined) {
                        $.ajax(contest.voteData['resource_uri'], {
                            'type': 'DELETE',
                        });
                        contest.voteData = undefined;
                    }
                } else if (contest.voteData == undefined) {
                    $.ajax(contest.uris['vote-list-uri'], {
                        'type': 'POST',
                        'data': JSON.stringify({
                            'contestvideo': contest.uris['contestvideo-uri'],
                            'user': contest.uris['user-uri'],
                            'vote': contest.vote,
                        }),
                        'contentType': 'application/json',
                        'success': contest.handleData,
                        'processData': false,
                    });
                } else {
                    $.ajax(contest.voteData['resource_uri'], {
                        'type': 'PUT',
                        'data': JSON.stringify({
                            'contestvideo': contest.voteData['contestvideo'],
                            'user': contest.voteData['user'],
                            'vote': contest.vote,
                        }),
                        'contentType': 'application/json',
                        'success': contest.handleData,
                        'processData': false,
                    });
                }
            }
        }
        contest.clickButton = function(){
            var $this = $(this);
            contest.setVote($this.hasClass(activeClass) ? '0' : $this.val());
            contest.sendVote();
        }
        contest.voteButtons['1'].on('click', contest.clickButton)
        contest.voteButtons['-1'].on('click', contest.clickButton)
    }
    $('.video-contest').each(function(index, element){
        contests.push(new Contest(element));
    });
});