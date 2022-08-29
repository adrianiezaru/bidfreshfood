$(".target").on("click", function() {
    let $button = $(this);
    let oldVal = parseInt($button.parent().find("input").val());
	let minVal = parseInt($button.parent().find("input").attr('min'));
    let newVal = 0;

    if ($button.text() == '+') {
        newVal = oldVal + 1;
    }

    else {
		if (oldVal > minVal){
			if (oldVal > 0) {
				newVal = oldVal - 1;
			}
			else {
				newVal = 0;
			}
		}
		else{
			newVal=oldVal;
		}
    }
	$button.parent().find('input').val(newVal+'€');
    $('[name="sendBid"]').val(newVal);
});





$('.addToCart').on("click", function(event) {
    if($(this).prev().prev().prev().find("input").val() == '0') {
        event.preventDefault();
        $(this).next().next().next().html("You need to select at least one shirt.");
        $(this).next().next().next().css("display", "block");
        $(this).next().next().next().delay(3000).slideUp();
    }

    if ($(this).prev().val() == "0") {
            event.preventDefault();
            $(this).next().next().next().html("You need to log in to buy.");
            $(this).next().next().next().css("display", "block");
            $(this).next().next().next().delay(3000).slideUp();
        }
});


$(".flashMessage").delay(3000).slideUp();

