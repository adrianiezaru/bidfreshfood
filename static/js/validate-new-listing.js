// The submit button
const SUBMIT = $( "#submit" );

// Each of the fields and error message divs
const bidTitle = $( "#bidTitle" );
const bidTitle_MSG = $( "#bidTitle-msg" );

const bidDescription = $( "#bidDescription" );
const bidDescription_MSG = $( "#bidDescription-msg" );

const bidImage = $( "#bidImage" );
const bidImage_MSG = $( "#bidImage-msg" );

const startingBid = $( "#startingBid" );
const startingBid_MSG = $( "#startingBid-msg" );

/**
 * Resets the error message fields and makes the submit
 * button visible.
 */
function reset_form ( )
{
    bidTitle_MSG.html( "" );
    bidTitle_MSG.hide();
    bidDescription_MSG.html( "" );
    bidDescription_MSG.hide();
    bidImage_MSG.html( "" );
    bidImage_MSG.hide();
    startingBid_MSG.html( "" );
    startingBid_MSG.hide();
    SUBMIT.show();
}

/**
 * Validates the information in the register form so that
 * the server is not required to check this information.
 */
function validate ( )
{
    let valid = true;
    reset_form ( );
    SUBMIT.hide();

    // This currently checks to see if the username is
    // present and if it is at least 5 characters in length.
    if ( !bidTitle.val() || bidTitle.val().length < 5  )
    {
        // Show an invalid input message
        bidTitle_MSG.html( "Title must be 5 characters or more" );
        bidTitle_MSG.show();
        // Indicate the type of bad input in the console.
        console.log( "Bad Title" );
        // Indicate that the form is invalid.
        valid = false;
    }


    if ( !bidDescription.val() || bidDescription.val().length < 10 )
    {
        bidDescription_MSG.html("Short Description needs to be at least 10 characters long");
        bidDescription_MSG.show();
        valid = false;
    }

    if ( !bidImage.val() )
    {
        bidImage_MSG.html("Image Path must not be empty");
        bidImage_MSG.show();
        valid = false;
    }

    if ( !startingBid.val()  || startingBid.val().length > 0 )
    {
        startingBid_MSG.html("Starting Bid must be greater than 0");
        startingBid_MSG.show();
        valid = false;
    }

    // If the form is valid, reset error messages
    if ( valid )
    {
        reset_form ( );
    }
}

// Bind the validate function to the required events.
$(document).ready ( validate );
bidTitle.change ( validate );
bidDescription.change ( validate );
bidImage.change ( validate );
startingBid.change ( validate );


