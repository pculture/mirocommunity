;(function($){
	
	var contests = window.localtv_contests = [],
		ContestWidget = function (element) {
			this.element = element;
			this.init();
		};
	
	// Define ContestWidget methods.
	ContestWidget.prototype = {
		init: function () {
			// Push this to the registry of contest widgets.
			window.localtv_contests.push(this);
			// Wipe the widget's current text.
			this.element.html('')
			// Create voting buttons.
			this.upvoteElement = $('<button class="upvote" value="1"><span class="vote-text">Vote Up</span> <span class="vote-count"></span></button>').appendTo(this.element);
			this.upvoteCountElement = this.upvoteElement.find('.vote-count').eq(0);
			if (this.data('downvotes') === 1){
				this.downvoteElement = $('<button class="downvote" value="-1"><span class="vote-text">Vote Down</span> <span class="vote-count"></span></button>').appendTo(this.element);
				this.downvoteCountElement = this.downvoteElement.find('.vote-count').eq(0);
			}
			// Bind the click event.
			this.bindClick();
			// Request the initial state of the votes.
			this.requestState();
		},
		bindClick: function () {
			var this_ = this;
			// Bind the click event.
			this.element.on('click.localtv.contest', 'button', function (event) { this_.clickHandler(event, this); })
		},
		unbindClick: function () {
			// Unbind the click event.
			this.element.off('click.localtv.contest', 'button');
		},
		data: function (arg) {
			// Shortcut to the element's data.
			return this.element.data(arg);
		},
		requestState: function () {
			// Triggers an AJAX request for the state of this user's votes on the contest
			// and the state of *all* votes on the contest.
			// Request completion triggers `this.receiveState`.
			var this_ = this,
				user_contest_vote_data = {'user': this.data('user'), 'contestvideo': this.data('contestvideo')},
				all_contest_vote_data = {'contestvideo': this.data('contestvideo')};
				
			this.startLoading();
			$.when(
				$.getJSON(this.data('contestvote-list-uri'), all_contest_vote_data),
				$.getJSON(this.data('contestvideo-detail-uri'), all_contest_vote_data)
			).then(function (user_vote_data, contest_video_data) { this_.receiveState(user_vote_data, contest_video_data); });
		},
		receiveState: function(user_vote_data, contest_video_data) {
			// Receives contest vote data, parses it out into the user vote, upvotes, and downvotes, then triggers the appropriate functions for displaying the data.
			var this_ = this,
				// find the current user's vote
				user_contest_vote = user_vote_data[0]['objects'][0] ? user_vote_data[0]['objects'][0] : undefined,
				// find upvotes and downvotes
				upvotes = contest_video_data[0]['upvotes'],
				downvotes = contest_video_data[0]['downvotes'];
			this.receiveUserVote(user_contest_vote);
			this.receiveVotes(upvotes, downvotes);
			this.endLoading();
		},
		receiveUserVote: function (data) {
			// Receives a contestvote object and updates the state of the buttons to reflect it.
			// Cache the current vote value.
			if (data === "") data = undefined; // Empty strings... can't live with them, can't live without them.
			this.voteData = data;
			// Clear the current state of buttons, regardless.
			this.element.find('.button-selected').removeClass('button-selected');
			// If the vote is undefined, stop here.
			if (this.voteData === undefined) return;
			// Update the button states.
			switch (this.voteData.vote) {
				case -1: // downvote
					this.downvoteElement.addClass('button-selected');
					break;
				case 1: // upvote
					this.upvoteElement.addClass('button-selected');
					break;
			}
		},
		receiveVotes: function (upvotes, downvotes) {
			// Expects upvotes, dowvotes as integers.
			// Updates the counts on the HTML elements.
			this.upvoteCountElement.html(upvotes);
			if (this.data('downvotes') === 1) this.downvoteCountElement.html(downvotes);
		},
		sendVote: function (vote) {
			// Sends an AJAX request to delete, create, or update a contestvote.
			// When the request completes, it triggers `this.requestState`.
			var this_ = this,
				request_uri, request_options = {};
			
			// If the user is not logged in, short-circuit and send them to the login page
			if (typeof this.data('user-detail-uri') === "undefined") return window.location = this.data('login-uri');
			
			if (vote === 0) {
				// Short-circuit if the vote matches the current state.
				if (this.voteData === undefined) return;
				// Otherwise, prepare a DELETE request.
				request_uri = this.voteData['resource_uri'];
				request_options.type = "DELETE";
			} else if (this.voteData == undefined) {
				// Prepare to POST a request to create a vote.
				request_uri = this.data('contestvote-list-uri')
				request_options.type = "POST";
			} else {
				// Prepate to PUT a request to update a vote.
				request_uri = this.voteData['resource_uri'];
				request_options.type = "PUT";
			}
			// Prepare the rest of the request.
			request_options.data = JSON.stringify({
					'contestvideo': this.data('contestvideo-detail-uri'),
					'user': this.data('user-detail-uri'),
					'vote': vote,
				});
			request_options.contentType = "application/json";
			request_options.processData = false;
			request_options.success = function (data) { this_.requestState() };
			// Send the request.
			this.startLoading();
			$.ajax(request_uri, request_options);
		},
		clickHandler: function (event, button) {
			var $button = $(button);
			// If the button already is active, take this as switching to a vote for 0.
			if ($button.hasClass('button-selected')){
				this.sendVote(0);
			} else {
				this.sendVote($button.val())
			}
			return false;
		},
		startLoading: function () {
			this.element.find('button').attr({disabled:"disabled"});
			this.unbindClick();
		},
		endLoading: function () {
			this.element.find('button').attr({disabled:false})
			this.bindClick();
		}
	}
	
	// Add a jQuery shortcut.
	$.fn.contestwidget = function (options) {
		return this.each(function () {
			var $this = $(this), data = $this.data('contestwidget');
			// if contestwidget has not been initialized on this element, do so
			if (!data) {
				$this.data('contestwidget', new ContestWidget($this));
			// otherwise, issue a contestwidget command
			} else if (typeof options == 'string') {
				data[options]();
			}
		});
	};
	
	// On domready, initialize all elements with class `.video-contest-vote-widget`.
	$(function(){
		$('.video-contest-vote-widget').contestwidget();
	});
	
}(jQuery));