// DOM Labeler

let labels = [];

function unmarkPage() {
    console.log('unmarkPage');
    while (labels.length > 0) {
        for (let i = labels.length - 1; i >= 0; i--) {
            document.body.removeChild(labels[i]);
            labels.pop();
        }
    }
    // console.log('All labels have been removed:', labels);
}

function getControlNameAndType(element) {
    let name = '';
    // 检查元素的标签名称
    let type = element.tagName ? element.tagName.toLowerCase() : '';

    let className = element.className;

    let value = element.value;

    // 如果元素是输入元素，则根据输入类型设置名称
    if (type === 'input') {
        // Ensure element.getAttribute('type') is not null before calling toLowerCase
        const inputType = element.getAttribute('type') ? element.getAttribute('type').toLowerCase() : '';
        switch (inputType) {
            case 'text':
                name = '文本输入框';
                break;
            case 'password':
                name = '密码输入框';
                break;
            // 添加其他输入类型
            default:
                name = value;
                break;
        }
    } else if (type === 'button' || (type === 'a' && element.role === 'button')) {
        name = element.textContent.trim() + '按钮';
    } else if (type === 'select') {
        name = '选择列表';
    }
    // 如果元素没有名称，则使用元素的文本内容作为名称
    if (!name && element.textContent.trim().length > 0) {
        name = element.textContent.trim();
    }

    return {name, type, className, value};
}

function markPage() {
    unmarkPage();
    // console.log('markPage');
    // 初始化 itemsData 对象
    var itemsData = {};

    // 获取页面主体元素的位置信息
    var bodyRect = document.body.getBoundingClientRect();

    // 获取页面上的所有元素
    var items = Array.prototype.slice.call(
        document.querySelectorAll('*')
    ).map(function (element) {
        // 计算元素的大小和位置
        var vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        var vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

        var rects = [...element.getClientRects()].filter(bb => {
            var center_x = bb.left + bb.width / 2;
            var center_y = bb.top + bb.height / 2;
            var elAtCenter = document.elementFromPoint(center_x, center_y);

            return elAtCenter === element || element.contains(elAtCenter);
        }).map(bb => {
            const rect = {
                left: Math.max(0, bb.left),
                top: Math.max(0, bb.top),
                right: Math.min(vw, bb.right),
                bottom: Math.min(vh, bb.bottom)
            };
            return {
                ...rect,
                width: rect.right - rect.left,
                height: rect.bottom - rect.top
            };
        });


        var area = rects.reduce((acc, rect) => acc + rect.width * rect.height, 0);

        // 返回包含元素信息、面积和矩形信息的对象
        return {
            element: element,
            include: (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.tagName === "SELECT") ||
                (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor === "pointer") ||
                (element.tagName === "IFRAME" || element.tagName === "VIDEO"),
            area,
            rects,
            text: element.textContent.trim().replace(/\s{2,}/g, ' ')
        };
    }).filter(item =>
        item.include && (item.area >= 20)
    );

    // 过滤掉内部可点击的项
    items = items.filter(x => !items.some(y => x.element.contains(y.element) && !(x === y)));

    // 生成随机颜色的函数
    function getRandomColor() {
        // console.log('getRandomColor');
        var letters = '0123456789ABCDEF';
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }

    var index = 0;
    // 在元素上创建浮动边框，使其始终可见
    items.forEach(function (item, index) {
        item.rects.forEach((bbox) => {
            var newElement = document.createElement("div");
            var borderColor = getRandomColor();
            newElement.style.outline = `2px dashed ${borderColor}`;
            newElement.style.position = "fixed";
            newElement.style.left = bbox.left + "px";
            newElement.style.top = bbox.top + "px";
            newElement.style.width = bbox.width + "px";
            newElement.style.height = bbox.height + "px";
            newElement.style.pointerEvents = "none";
            newElement.style.boxSizing = "border-box";
            newElement.style.zIndex = 214748364;
            // 添加浮动标签
            var label = document.createElement("span");
            label.textContent = index;
            label.style.position = "absolute";
            label.style.top = "-20px";
            label.style.left = "0px";
            label.style.background = borderColor;
            label.style.color = "white";
            label.style.padding = "2px 4px";
            label.style.fontSize = "12px";
            label.style.borderRadius = "2px";
            newElement.appendChild(label);

            // 将新元素添加到页面中
            document.body.appendChild(newElement);
            labels.push(newElement);

            // 获取控件的名称和类别
            const {name, type, className, value} = getControlNameAndType(item.element);
            itemsData[index] = {
                name: name, // 控件名称
                // placeholder: placeholder,
                type: type, // 控件类别
                className: className,
                value: value,
                // x: bbox.left.toString(),
                // y: bbox.top.toString(),
                // w: bbox.width.toString(),
                // h: bbox.height.toString(),
                // center_x: (bbox.left + bbox.width / 2).toString(),
                // center_y: (bbox.top + bbox.height / 2).toString()
                x: (bbox.left + bbox.width / 2).toString(),
                y: (bbox.top + bbox.height / 2).toString()
            };
        });
    });
    // unmarkPage();
    // 返回包含标注信息的对象
    return itemsData; // Return the populated itemsData object
}
