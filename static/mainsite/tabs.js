/***************************/
//@Author: Adrian "yEnS" Mato Gondelle & Ivan Guardado Castro
//@website: www.yensdesign.com
//@email: yensamg@gmail.com
//@license: Feel free to use it, but keep this credits please!
/***************************/

$(document).ready(function(){
	$("#featuresnav > li").click(function(e){
		switch(e.target.id){
			case "management":
				//change status & style menu
				$("#management").addClass("current");
				$("#presentation").removeClass("current");
				$("#engagement").removeClass("current");
				$("#morefeatures").removeClass("current");
				//display selected division, hide others
				$("div.management").fadeIn();
				$("div.presentation").css("display", "none");
				$("div.engagement").css("display", "none");
				$("div.morefeatures").css("display", "none");
			break;
			case "presentation":
				//change status & style menu
				$("#management").removeClass("current");
				$("#presentation").addClass("current");
				$("#engagement").removeClass("current");
				$("#morefeatures").removeClass("current");
				//display selected division, hide others
				$("div.presentation").fadeIn();
				$("div.management").css("display", "none");
				$("div.engagement").css("display", "none");
				$("div.morefeatures").css("display", "none");
			break;
			case "engagement":
				//change status & style menu
				$("#management").removeClass("current");
				$("#presentation").removeClass("current");
				$("#engagement").addClass("current");
				$("#morefeatures").removeClass("current");
				//display selected division, hide others
				$("div.engagement").fadeIn();
				$("div.presentation").css("display", "none");
				$("div.management").css("display", "none");
				$("div.morefeatures").css("display", "none");
			break;
			case "morefeatures":
				//change status & style menu
				$("#management").removeClass("current");
				$("#presentation").removeClass("current");
				$("#engagement").removeClass("current");
				$("#morefeatures").addClass("current");
				//display selected division, hide others
				$("div.morefeatures").fadeIn();
				$("div.presentation").css("display", "none");
				$("div.management").css("display", "none");
				$("div.engagement").css("display", "none");
			break;
		}
		//alert(e.target.id);
		return false;
	});
});
