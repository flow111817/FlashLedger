/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3174063690")

  // update field
  collection.fields.addAt(2, new Field({
    "hidden": false,
    "id": "select105650625",
    "maxSelect": 1,
    "name": "category",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "必要饮食",
      "次要饮食",
      "交通出行",
      "休闲娱乐",
      "生活消费",
      "医疗保健",
      "工资薪金"
    ]
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3174063690")

  // update field
  collection.fields.addAt(2, new Field({
    "hidden": false,
    "id": "select105650625",
    "maxSelect": 1,
    "name": "category",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "必要饮食",
      "次要饮食",
      "交通出行",
      "休闲娱乐",
      "生活消费",
      "医疗保健"
    ]
  }))

  return app.save(collection)
})
