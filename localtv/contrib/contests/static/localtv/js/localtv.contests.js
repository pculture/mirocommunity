;jQuery(function($){
	$('.video-contest').on('submit.localtv.contest', 'form', function (e) {
		var $this = $(this);
		$.ajax({
			type: 'POST',
			url: $this.attr('action'),
			dataType: 'application/json',
			contentType: 'application/json',
			data: JSON.stringify({
				contestvideo: $this.find('[name="contestvideo"]').val(),
				vote: $this.find('[name="vote"]').val()
			}),
			processData:  false
		})
		return false;
	});
});