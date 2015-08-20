/**
 * This is a simple component that renders add buttons for all available XBlock template types.
 */
define(["jquery", "underscore", "gettext", "js/views/baseview", "js/views/utils/view_utils",
        "js/views/components/add_xblock_button", "js/views/components/add_xblock_menu"],
    function ($, _, gettext, BaseView, ViewUtils, AddXBlockButton, AddXBlockMenu) {
        var AddXBlockComponent = BaseView.extend({
            events: {
                'click .new-component .new-component-type button.multiple-templates': 'showComponentTemplates',
                'click .new-component .new-component-type button.single-template': 'createNewComponent',
                'click .new-component .cancel-button': 'closeNewComponent',
                'click .new-component-templates .new-component-template button': 'createNewComponent',
                'click .new-component-templates .cancel-button': 'closeNewComponent'
            },

            initialize: function(options) {
                BaseView.prototype.initialize.call(this, options);
                this.template = this.loadTemplate('add-xblock-component');
            },

            render: function () {
                if (!this.$el.html()) {
                    var that = this;
                    this.$el.html(this.template({}));
                    this.collection.each(
                        function (componentModel) {
                            var view, menu;

                            view = new AddXBlockButton({model: componentModel});
                            that.$el.find('.new-component-type').append(view.render().el);

                            menu = new AddXBlockMenu({model: componentModel});
                            that.$el.append(menu.render().el);
                        }
                    );
                }
            },

            showComponentTemplates: function(event) {
                var type;
                event.preventDefault();
                event.stopPropagation();
                type = $(event.currentTarget).data('type');
                this.$('.new-component').slideUp(250);
                this.$('.new-component-' + type).slideDown(250);
                this.$('.new-component-' + type + ' ul').focus();
            },

            closeNewComponent: function(event) {
                event.preventDefault();
                event.stopPropagation();
                type = $(event.currentTarget).data('type');
                this.$('.new-component').slideDown(250);
                this.$('.new-component-templates').slideUp(250);
                this.$('ul.new-component-type li button[data-type=' + type + ']').focus();

            },

            createNewComponent: function(event) {
                var self = this,
                    element = $(event.currentTarget),
                    saveData = element.data(),
                    oldOffset = ViewUtils.getScrollOffset(this.$el);
                event.preventDefault();
                this.closeNewComponent(event);
                ViewUtils.runOperationShowingMessage(
                    gettext('Adding'),
                    _.bind(this.options.createComponent, this, saveData, element)
                ).always(function() {
                    // Restore the scroll position of the buttons so that the new
                    // component appears above them.
                    ViewUtils.setScrollOffset(self.$el, oldOffset);
                });
            }
        });

        return AddXBlockComponent;
    }); // end define();
