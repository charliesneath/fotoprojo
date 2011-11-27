$(document).ready(function() {	
	$('.photo').click(function() 
	{
		$('#lightbox').toggle(
    		function() {
    			$(this).fadeIn;
    		},
    		function() {
    			$(this).fadeOut;
		    }
		)
	})
})