[Page 122]

<image> image <image>

Figure 3-3. Decision threshold and precision/recall tradeoff

Scikit-Learn does not let you set the threshold directly, but it does give you access to the decision scores that it uses to make predictions. Instead of calling the classifier’s predict()  method, you can call its  decision_function()  method, which returns a score for each instance, and then make predictions based on those scores using any threshold you want:

>>>  y_scores   =   sgd_clf . decision_function ([ some_digit ]) >>>  y_scores array([2412.53175101]) >>>  threshold   =   0 >>>  y_some_digit_pred   =  ( y_scores   >   threshold ) array([ True])

The  SGDClassifier  uses a threshold equal to 0, so the previous code returns the same result as the  predict()  method (i.e.,  True ). Let’s raise the threshold:

>>>  threshold   =   8000 >>>  y_some_digit_pred   =  ( y_scores   >   threshold ) >>>  y_some_digit_pred array([False])

This confirms that raising the threshold decreases recall. The image actually repre‐ sents a 5, and the classifier detects it when the threshold is 0, but it misses it when the threshold is increased to 8,000.

Now how do you decide which threshold to use? For this you will first need to get the scores of all instances in the training set using the  cross_val_predict()  function again, but this time specifying that you want it to return decision scores instead of predictions:

y_scores   =   cross_val_predict ( sgd_clf ,  X_train ,  y_train_5 ,  cv = 3 ,                               method = "decision_function" )

Now with these scores you can compute precision and recall for all possible thresh‐ olds using the  precision_recall_curve()  function:

96  |  Chapter 3: Classification

